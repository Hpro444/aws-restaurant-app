"""Service that builds and upserts weekly WaiterReport rows from SQS events."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

from commons.app_config import AppConfig
from commons.log_helper import logger
from commons.report_utils import parse_date, pct_delta, period_end_for, period_start_for
from domain.waiter_report import WaiterReport
from dto.feedback_event import FeedbackEventMessage
from dto.reservation_event import ReservationEventMessage, ReservationEventType
from enums import FeedbackType, ReservationStatus
from repositories.feedback_service_repository import FeedbackServiceRepository
from repositories.location_repository import LocationRepository
from repositories.order_repository import OrderRepository
from repositories.reservation_repository import ReservationRepository
from repositories.slot_repository import SlotRepository
from repositories.waiter_report_repository import WaiterReportRepository
from repositories.waiter_repository import WaiterRepository


class WaiterReportService:
    """Maintains the weekly WaiterReport table from reservation and feedback events.

    Each call to ``handle_reservation_event`` or ``handle_feedback_event``
    triggers a full recalculation of the relevant (waiter, ISO-week) row from
    the database so the row is always consistent regardless of event order.
    """

    def __init__(
        self,
        settings: AppConfig | None = None,
        waiter_report_repo: WaiterReportRepository | None = None,
        waiter_repo: WaiterRepository | None = None,
        location_repo: LocationRepository | None = None,
        reservation_repo: ReservationRepository | None = None,
        slot_repo: SlotRepository | None = None,
        feedback_service_repo: FeedbackServiceRepository | None = None,
        order_repo: OrderRepository | None = None,
    ) -> None:
        """Initialise repositories, creating defaults when omitted.

        Args:
            settings: Shared application config.
            waiter_report_repo: Optional WaiterReportRepository instance.
            waiter_repo: Optional WaiterRepository instance.
            location_repo: Optional LocationRepository instance.
            reservation_repo: Optional ReservationRepository instance.
            slot_repo: Optional SlotRepository instance.
            feedback_service_repo: Optional FeedbackServiceRepository instance.
            order_repo: Optional OrderRepository instance.

        """
        cfg = settings or AppConfig()
        self._waiter_report_repo = waiter_report_repo or WaiterReportRepository(cfg)
        self._waiter_repo = waiter_repo or WaiterRepository(cfg)
        self._location_repo = location_repo or LocationRepository(cfg)
        self._reservation_repo = reservation_repo or ReservationRepository(cfg)
        self._slot_repo = slot_repo or SlotRepository(cfg)
        self._feedback_service_repo = (
            feedback_service_repo or FeedbackServiceRepository(cfg)
        )
        self._order_repo = order_repo or OrderRepository(cfg)

    def handle_reservation_event(self, msg: ReservationEventMessage) -> None:
        """Update the waiter report when a reservation lifecycle event arrives.

        Only ``FINISHED`` events are processed; all others are skipped.

        Args:
            msg: Parsed reservation SQS event.

        """
        if msg.event_type != ReservationEventType.FINISHED:
            return
        if not msg.waiter_id:
            return
        event_date = parse_date(msg.date)
        self._upsert_report(UUID(msg.waiter_id), event_date)

    def handle_feedback_event(self, msg: FeedbackEventMessage) -> None:
        """Update the waiter report when a feedback event arrives.

        Only SERVICE-type feedback events are processed.

        Args:
            msg: Parsed feedback SQS event.

        """
        if msg.feedback_type != FeedbackType.SERVICE.value:
            return
        if not msg.waiter_id:
            return
        event_date = self._resolve_feedback_period_date(msg)
        self._upsert_report(UUID(msg.waiter_id), event_date)

    def _resolve_feedback_period_date(self, msg: FeedbackEventMessage) -> date:
        """Return the date used to choose the feedback's weekly report.

        Feedback is attributed to the reservation's dining week — consistent with
        how FINISHED reservations drive orders and revenue — so all metrics for a
        reservation land in the same weekly row. Falls back to the event timestamp
        when the reservation cannot be resolved.
        """
        if msg.reservation_id:
            reservation = self._reservation_repo.get(UUID(msg.reservation_id))
            if reservation is not None and reservation.date:
                return parse_date(reservation.date)
        return parse_date(msg.timestamp[:10])

    # ── Private helpers ─────────────────────────────────────────────

    def _upsert_report(self, waiter_id: UUID, event_date: date) -> None:
        """Recalculate and persist the WaiterReport row for (waiter, ISO-week).

        Args:
            waiter_id: UUID of the waiter.
            event_date: UTC date extracted from the triggering event.

        """
        period_start = period_start_for(event_date)
        period_end = period_end_for(period_start)

        waiter = self._waiter_repo.get(waiter_id)
        if waiter is None:
            logger.warning(
                "Waiter not found; skipping report upsert", waiter_id=str(waiter_id)
            )
            return

        location = self._location_repo.get(waiter.location_id)
        if location is None:
            logger.warning(
                "Location not found; skipping report upsert",
                location_id=str(waiter.location_id),
            )
            return

        all_slots = self._slot_repo.find_by_waiter_id_and_period(
            waiter_id, period_start, period_end
        )
        working_hours = len(all_slots) * 1.75

        reservations = self._reservation_repo.find_by_waiter_id_and_period(
            waiter_id,
            period_start.isoformat(),
            period_end.isoformat(),
        )
        finished = [r for r in reservations if r.status == ReservationStatus.FINISHED]
        orders_processed = sum(
            len(self._order_repo.find_by_reservation_id(r.id)) for r in finished
        )

        feedbacks = self._feedback_service_repo.find_by_waiter_id_and_period(
            waiter_id, period_start, period_end
        )
        fb_count = len(feedbacks)
        fb_sum = float(sum(f.rate for f in feedbacks if f.rate is not None))
        avg_fb = round(fb_sum / fb_count, 2) if fb_count else None
        min_fb = min((f.rate for f in feedbacks if f.rate is not None), default=None)

        prev_period_start = period_start_for(
            period_start - timedelta(days=7)
        ).isoformat()
        prev = self._waiter_report_repo.find_by_waiter_and_period(
            waiter_id, prev_period_start
        )

        orders_delta = pct_delta(
            orders_processed, prev.orders_processed if prev else None
        )
        feedback_delta = pct_delta(avg_fb, prev.avg_service_feedback if prev else None)

        existing = self._waiter_report_repo.find_by_waiter_and_period(
            waiter_id, period_start.isoformat()
        )
        report_id = existing.id if existing else uuid4()

        report = WaiterReport(
            id=report_id,
            waiter_id=waiter_id,
            location_id=waiter.location_id,
            location_name=location.name,
            waiter_first_name=waiter.fname,
            waiter_last_name=waiter.lname,
            waiter_email=waiter.email,
            report_period_start=period_start.isoformat(),
            report_period_end=period_end.isoformat(),
            working_hours=working_hours,
            orders_processed=orders_processed,
            service_feedback_count=fb_count,
            service_feedback_sum=fb_sum,
            avg_service_feedback=avg_fb,
            min_service_feedback=min_fb,
            orders_processed_delta_pct=orders_delta,
            avg_service_feedback_delta_pct=feedback_delta,
        )
        self._waiter_report_repo.update(report)
        logger.info(
            "WaiterReport upserted",
            waiter_id=str(waiter_id),
            period_start=period_start.isoformat(),
            orders_processed=orders_processed,
            working_hours=working_hours,
        )

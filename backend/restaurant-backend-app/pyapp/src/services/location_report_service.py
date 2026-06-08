"""Service that builds and upserts weekly LocationReport rows from SQS events."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

from commons.app_config import AppConfig
from commons.log_helper import logger
from commons.report_utils import parse_date, pct_delta, period_end_for, period_start_for
from domain.location_report import LocationReport
from dto.feedback_event import FeedbackEventMessage
from dto.reservation_event import ReservationEventMessage, ReservationEventType
from enums import FeedbackType, ReservationStatus
from repositories.dish_repository import DishRepository
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.location_report_repository import LocationReportRepository
from repositories.location_repository import LocationRepository
from repositories.order_repository import OrderRepository
from repositories.reservation_repository import ReservationRepository
from repositories.waiter_repository import WaiterRepository


class LocationReportService:
    """Maintains the weekly LocationReport table from reservation and feedback events.

    Each call to ``handle_reservation_event`` or ``handle_feedback_event``
    triggers a full recalculation of the relevant (location, ISO-week) row from
    the database so the row is always consistent regardless of event order.
    """

    def __init__(
        self,
        settings: AppConfig | None = None,
        location_report_repo: LocationReportRepository | None = None,
        location_repo: LocationRepository | None = None,
        waiter_repo: WaiterRepository | None = None,
        reservation_repo: ReservationRepository | None = None,
        feedback_cuisine_repo: FeedbackCuisineRepository | None = None,
        order_repo: OrderRepository | None = None,
        dish_repo: DishRepository | None = None,
    ) -> None:
        """Initialise repositories, creating defaults when omitted.

        Args:
            settings: Shared application config.
            location_report_repo: Optional LocationReportRepository instance.
            location_repo: Optional LocationRepository instance.
            waiter_repo: Optional WaiterRepository instance.
            reservation_repo: Optional ReservationRepository instance.
            feedback_cuisine_repo: Optional FeedbackCuisineRepository instance.
            order_repo: Optional OrderRepository instance.
            dish_repo: Optional DishRepository instance.

        """
        cfg = settings or AppConfig()
        self._location_report_repo = location_report_repo or LocationReportRepository(
            cfg
        )
        self._location_repo = location_repo or LocationRepository(cfg)
        self._waiter_repo = waiter_repo or WaiterRepository(cfg)
        self._reservation_repo = reservation_repo or ReservationRepository(cfg)
        self._feedback_cuisine_repo = (
            feedback_cuisine_repo or FeedbackCuisineRepository(cfg)
        )
        self._order_repo = order_repo or OrderRepository(cfg)
        self._dish_repo = dish_repo or DishRepository(cfg)

    def handle_reservation_event(self, msg: ReservationEventMessage) -> None:
        """Update the location report when a reservation lifecycle event arrives.

        Only ``FINISHED`` events with a known ``location_id`` are processed.

        Args:
            msg: Parsed reservation SQS event.

        """
        if msg.event_type != ReservationEventType.FINISHED:
            return
        if not msg.location_id:
            return
        event_date = parse_date(msg.date)
        self._upsert_report(UUID(msg.location_id), event_date)

    def handle_feedback_event(self, msg: FeedbackEventMessage) -> None:
        """Update the location report when a cuisine feedback event arrives.

        Only ``CUISINE`` feedback events with a known ``location_id`` are processed.

        Args:
            msg: Parsed feedback SQS event.

        """
        if msg.feedback_type != FeedbackType.CULINARY.value:
            return
        if not msg.location_id:
            return
        event_date = self._resolve_feedback_period_date(msg)
        self._upsert_report(UUID(msg.location_id), event_date)

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

    def _upsert_report(self, location_id: UUID, event_date) -> None:
        """Recalculate and persist the LocationReport row for (location, ISO-week).

        Args:
            location_id: UUID of the location.
            event_date: UTC date extracted from the triggering event.

        """
        p_start = period_start_for(event_date)
        p_end = period_end_for(p_start)

        location = self._location_repo.get(location_id)
        if location is None:
            logger.warning(
                "Location not found; skipping location report upsert",
                location_id=str(location_id),
            )
            return

        waiters = self._waiter_repo.find_by_location_id(location_id)
        finished_ids: list[UUID] = []
        for waiter in waiters:
            reservations = self._reservation_repo.find_by_waiter_id_and_period(
                waiter.id, p_start.isoformat(), p_end.isoformat()
            )
            finished_ids.extend(
                r.id for r in reservations if r.status == ReservationStatus.FINISHED
            )
        orders_processed, revenue = self._collect_orders_and_revenue(finished_ids)

        feedbacks = self._feedback_cuisine_repo.find_by_location_id_and_period(
            location_id, p_start, p_end
        )
        fb_count = len(feedbacks)
        fb_sum = float(sum(f.rate for f in feedbacks if f.rate is not None))
        avg_fb = round(fb_sum / fb_count, 2) if fb_count else None
        min_fb = min((f.rate for f in feedbacks if f.rate is not None), default=None)

        prev_period_start = period_start_for(p_start - timedelta(days=7)).isoformat()
        prev = self._location_report_repo.find_by_location_and_period(
            location_id, prev_period_start
        )

        orders_delta = pct_delta(
            orders_processed, prev.orders_processed if prev else None
        )
        feedback_delta = pct_delta(avg_fb, prev.avg_cuisine_feedback if prev else None)
        revenue_delta = pct_delta(revenue, prev.revenue if prev else None)

        existing = self._location_report_repo.find_by_location_and_period(
            location_id, p_start.isoformat()
        )
        report_id = existing.id if existing else uuid4()

        report = LocationReport(
            id=report_id,
            location_id=location_id,
            location_name=location.name,
            report_period_start=p_start.isoformat(),
            report_period_end=p_end.isoformat(),
            orders_processed=orders_processed,
            orders_processed_delta_pct=orders_delta,
            cuisine_feedback_count=fb_count,
            cuisine_feedback_sum=fb_sum,
            avg_cuisine_feedback=avg_fb,
            min_cuisine_feedback=min_fb,
            avg_cuisine_feedback_delta_pct=feedback_delta,
            revenue=revenue,
            revenue_delta_pct=revenue_delta,
        )
        self._location_report_repo.update(report)
        logger.info(
            "LocationReport upserted",
            location_id=str(location_id),
            period_start=p_start.isoformat(),
            orders_processed=orders_processed,
            revenue=revenue,
            cuisine_feedback_count=fb_count,
        )

    def _collect_orders_and_revenue(
        self, reservation_ids: list[UUID]
    ) -> tuple[int, float]:
        """Return (order_count, total_revenue) for the given finished reservations.

        Fetches every Order for each reservation, then prices each line item via
        the dish catalogue.  A local cache avoids redundant dish lookups within a
        single call.  If a dish is not found its price is treated as 0.0.

        Args:
            reservation_ids: IDs of finished reservations to aggregate.

        Returns:
            Tuple of (total order count, total revenue in USD).

        """
        order_count = 0
        revenue = 0.0
        dish_price_cache: dict[UUID, float] = {}
        for res_id in reservation_ids:
            orders = self._order_repo.find_by_reservation_id(res_id)
            order_count += len(orders)
            for order in orders:
                for item in order.items:
                    if item.dish_id not in dish_price_cache:
                        dish = self._dish_repo.get(item.dish_id)
                        dish_price_cache[item.dish_id] = dish.price if dish else 0.0
                    revenue += item.quantity * dish_price_cache[item.dish_id]
        return order_count, revenue

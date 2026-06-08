"""Unit tests for WaiterReportService report upsert logic."""

from datetime import UTC, date, datetime
from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.report_utils import (
        parse_date,
        pct_delta,
        period_end_for,
        period_start_for,
    )
    from domain.feedback import FeedbackService as ServiceFeedback
    from domain.location import Location
    from domain.order import Order
    from domain.order_item import OrderItem
    from domain.reservation import Reservation
    from domain.slot import Slot
    from domain.user import Waiter
    from domain.waiter_report import WaiterReport
    from dto.feedback_event import FeedbackEventMessage, FeedbackEventType
    from dto.reservation_event import ReservationEventMessage, ReservationEventType
    from dto.reservation_management import AllowedActions
    from enums import FeedbackType, ReservationStatus, SlotStatus
    from services.waiter_report_service import WaiterReportService


# ── Fixtures ──────────────────────────────────────────────────────────────────

_WAITER_ID = uuid4()
_LOCATION_ID = uuid4()
_PERIOD_DATE = date(2026, 6, 4)  # Wednesday in week Mon 2026-06-01 – Sun 2026-06-07


def _make_waiter() -> Waiter:
    """Return a Waiter domain object for tests."""
    return Waiter(
        id=_WAITER_ID,
        fname="Alex",
        lname="Coper",
        email="alexcop@gmail.com",
        image_url="",
        location_id=_LOCATION_ID,
    )


def _make_location() -> Location:
    """Return a Location domain object for tests."""
    from datetime import time as t

    return Location(
        id=_LOCATION_ID,
        name="Location 1",
        address="1 Main St",
        description="",
        image_url="",
        open_time=t(9, 0),
        close_time=t(22, 0),
    )


def _make_reservation(
    status: ReservationStatus = ReservationStatus.FINISHED,
) -> Reservation:
    """Return a minimal Reservation on _PERIOD_DATE."""
    slot_id = uuid4()
    return Reservation(
        id=uuid4(),
        customer_id=uuid4(),
        waiter_id=_WAITER_ID,
        created_at=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
        slot_ids=[slot_id],
        status=status,
        number_of_guests=2,
        date="2026-06-04",
    )


def _make_slot() -> Slot:
    """Return a minimal Slot."""
    return Slot(
        id=uuid4(),
        table_id=uuid4(),
        start_time=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 6, 4, 11, 30, tzinfo=UTC),
        date=datetime(2026, 6, 4, tzinfo=UTC),
        status=SlotStatus.RESERVED,
    )


def _make_order(reservation_id=None) -> Order:
    """Return a minimal Order linked to the given reservation."""
    from datetime import UTC, datetime

    return Order(
        id=uuid4(),
        reservation_id=reservation_id or uuid4(),
        waiter_id=_WAITER_ID,
        items=[OrderItem(dish_id=uuid4(), quantity=1)],
        created_at=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
    )


def _make_feedback(rate: int = 4) -> ServiceFeedback:
    """Return a minimal FeedbackService record."""
    return ServiceFeedback(
        id=uuid4(),
        reservation_id=uuid4(),
        customer_id=uuid4(),
        feedback="Good",
        rate=rate,
        date=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        waiter_id=_WAITER_ID,
    )


def _make_service(
    reservations=None,
    slots=None,
    feedbacks=None,
    existing_report=None,
    prev_report=None,
    orders_per_reservation: int = 1,
) -> WaiterReportService:
    """Build a WaiterReportService with fully mocked repositories."""
    waiter_report_repo = MagicMock()
    waiter_report_repo.find_by_waiter_and_period.side_effect = lambda wid, ps: (
        prev_report if ps == "2026-05-25" else existing_report
    )

    waiter_repo = MagicMock()
    waiter_repo.get.return_value = _make_waiter()

    location_repo = MagicMock()
    location_repo.get.return_value = _make_location()

    reservation_repo = MagicMock()
    reservation_repo.find_by_waiter_id_and_period.return_value = reservations or []
    reservation_repo.get.return_value = _make_reservation()

    slot_repo = MagicMock()
    slot_repo.find_by_waiter_id_and_period.return_value = slots or []

    feedback_repo = MagicMock()
    feedback_repo.find_by_waiter_id_and_period.return_value = feedbacks or []

    order_repo = MagicMock()
    order_repo.find_by_reservation_id.side_effect = lambda rid: [
        _make_order(rid) for _ in range(orders_per_reservation)
    ]

    return WaiterReportService(
        waiter_report_repo=waiter_report_repo,
        waiter_repo=waiter_repo,
        location_repo=location_repo,
        reservation_repo=reservation_repo,
        slot_repo=slot_repo,
        feedback_service_repo=feedback_repo,
        order_repo=order_repo,
    )


def _make_reservation_event(
    event_type: ReservationEventType = ReservationEventType.FINISHED,
) -> ReservationEventMessage:
    """Return a minimal ReservationEventMessage."""
    return ReservationEventMessage(
        event_type=event_type,
        timestamp="2026-06-04T10:00:00Z",
        reservation_id=str(uuid4()),
        status=ReservationStatus.FINISHED,
        waiter_id=str(_WAITER_ID),
        location_id=str(_LOCATION_ID),
        date="2026-06-04",
        time_from="10:00",
        time_to="11:30",
        guests_number=2,
        allowed_actions=AllowedActions(can_edit=False, can_cancel=False),
    )


def _make_feedback_event(
    feedback_type: str = FeedbackType.SERVICE.value,
    rate: int = 4,
) -> FeedbackEventMessage:
    """Return a minimal FeedbackEventMessage."""
    return FeedbackEventMessage(
        event_type=FeedbackEventType.CREATED,
        feedback_id=str(uuid4()),
        reservation_id=str(uuid4()),
        customer_id=str(uuid4()),
        feedback="Good",
        rate=rate,
        date="2026-06-04T12:00:00Z",
        feedback_type=feedback_type,
        waiter_id=str(_WAITER_ID),
        timestamp="2026-06-04T12:00:00Z",
    )


# ── Period helper tests ───────────────────────────────────────────────────────


class TestPeriodHelpers(TestCase):
    """Tests for module-level date helper functions."""

    def test_period_start_is_monday(self):
        """Period start is the Monday of the ISO week containing the given date."""
        self.assertEqual(period_start_for(date(2026, 6, 4)), date(2026, 6, 1))
        self.assertEqual(period_start_for(date(2026, 6, 1)), date(2026, 6, 1))
        self.assertEqual(period_start_for(date(2026, 6, 7)), date(2026, 6, 1))

    def test_period_end_is_sunday(self):
        """Period end is 6 days after period start."""
        self.assertEqual(period_end_for(date(2026, 6, 1)), date(2026, 6, 7))

    def testparse_date_from_iso_date(self):
        """Short date strings 'YYYY-MM-DD' are parsed correctly."""
        self.assertEqual(parse_date("2026-06-04"), date(2026, 6, 4))

    def testparse_date_from_iso_datetime(self):
        """ISO-8601 UTC datetime strings are parsed to UTC date."""
        self.assertEqual(parse_date("2026-06-04T23:00:00Z"), date(2026, 6, 4))

    def testpct_delta_calculates_correctly(self):
        """Delta percentage is rounded to 2 decimal places."""
        self.assertEqual(pct_delta(11, 10), 10.0)
        self.assertEqual(pct_delta(9, 10), -10.0)

    def testpct_delta_returns_none_when_no_previous(self):
        """Delta is None when previous is None or zero."""
        self.assertIsNone(pct_delta(5, None))
        self.assertIsNone(pct_delta(5, 0))


# ── Reservation event handling ────────────────────────────────────────────────


class TestHandleReservationEvent(TestCase):
    """Tests for WaiterReportService.handle_reservation_event."""

    def test_skips_non_finished_events(self):
        """Non-FINISHED events do not trigger a report upsert."""
        service = _make_service()
        service.handle_reservation_event(
            _make_reservation_event(ReservationEventType.CREATED)
        )
        service._waiter_report_repo.update.assert_not_called()

    def test_skips_events_without_waiter(self):
        """Events with no waiter_id do not trigger a report upsert."""
        service = _make_service()
        msg = _make_reservation_event()
        msg.waiter_id = None
        service.handle_reservation_event(msg)
        service._waiter_report_repo.update.assert_not_called()

    def test_skips_when_waiter_not_found(self):
        """No upsert when the waiter does not exist in the database."""
        service = _make_service()
        service._waiter_repo.get.return_value = None
        service.handle_reservation_event(_make_reservation_event())
        service._waiter_report_repo.update.assert_not_called()

    def test_creates_new_report_on_first_event(self):
        """A new WaiterReport row is created when none exists for the period."""
        reservation = _make_reservation()
        slot = _make_slot()
        service = _make_service(reservations=[reservation], slots=[slot])

        service.handle_reservation_event(_make_reservation_event())

        service._waiter_report_repo.update.assert_called_once()
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertEqual(str(report.waiter_id), str(_WAITER_ID))
        self.assertEqual(report.report_period_start, "2026-06-01")
        self.assertEqual(report.report_period_end, "2026-06-07")
        self.assertEqual(report.orders_processed, 1)
        self.assertAlmostEqual(report.working_hours, 1.75)

    def test_preserves_existing_report_id(self):
        """When a row already exists for the period, its id is preserved."""
        existing_id = uuid4()
        existing = WaiterReport(
            id=existing_id,
            waiter_id=_WAITER_ID,
            location_id=_LOCATION_ID,
            location_name="Location 1",
            waiter_first_name="Alex",
            waiter_last_name="Coper",
            waiter_email="alexcop@gmail.com",
            report_period_start="2026-06-01",
            report_period_end="2026-06-07",
            working_hours=1.75,
            orders_processed=1,
            service_feedback_count=0,
            service_feedback_sum=0.0,
        )
        service = _make_service(
            reservations=[_make_reservation()],
            slots=[_make_slot()],
            existing_report=existing,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertEqual(report.id, existing_id)

    def test_counts_only_finished_reservations_for_orders(self):
        """Working hours include cancelled slots; orders_processed only counts FINISHED."""
        finished = _make_reservation(ReservationStatus.FINISHED)
        cancelled = _make_reservation(ReservationStatus.CANCELLED)
        slots = [_make_slot(), _make_slot()]
        service = _make_service(reservations=[finished, cancelled], slots=slots)
        service.handle_reservation_event(_make_reservation_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertEqual(report.orders_processed, 1)
        self.assertAlmostEqual(report.working_hours, 2 * 1.75)

    def test_calculates_delta_against_previous_period(self):
        """Delta percentage is computed from the previous ISO week's row."""
        prev = WaiterReport(
            id=uuid4(),
            waiter_id=_WAITER_ID,
            location_id=_LOCATION_ID,
            location_name="Location 1",
            waiter_first_name="Alex",
            waiter_last_name="Coper",
            waiter_email="alexcop@gmail.com",
            report_period_start="2026-05-25",
            report_period_end="2026-05-31",
            working_hours=1.75,
            orders_processed=10,
            service_feedback_count=0,
            service_feedback_sum=0.0,
        )
        service = _make_service(
            reservations=[_make_reservation()],
            slots=[_make_slot()],
            prev_report=prev,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertIsNotNone(report.orders_processed_delta_pct)
        self.assertAlmostEqual(report.orders_processed_delta_pct, -90.0)

    def test_no_delta_when_no_previous_period(self):
        """Delta is None when there is no previous period row."""
        service = _make_service(
            reservations=[_make_reservation()], slots=[_make_slot()]
        )
        service.handle_reservation_event(_make_reservation_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertIsNone(report.orders_processed_delta_pct)


# ── Feedback event handling ───────────────────────────────────────────────────


class TestHandleFeedbackEvent(TestCase):
    """Tests for WaiterReportService.handle_feedback_event."""

    def test_skips_culinary_feedback(self):
        """CULINARY feedback events do not trigger a report upsert."""
        service = _make_service()
        service.handle_feedback_event(_make_feedback_event(FeedbackType.CULINARY.value))
        service._waiter_report_repo.update.assert_not_called()

    def test_skips_events_without_waiter(self):
        """Feedback events with no waiter_id do not trigger a report upsert."""
        service = _make_service()
        msg = _make_feedback_event()
        msg.waiter_id = None
        service.handle_feedback_event(msg)
        service._waiter_report_repo.update.assert_not_called()

    def test_stores_feedback_stats(self):
        """Feedback count, sum, avg, and min are computed from the DB query result."""
        feedbacks = [_make_feedback(rate=4), _make_feedback(rate=5)]
        service = _make_service(feedbacks=feedbacks)
        service.handle_feedback_event(_make_feedback_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertEqual(report.service_feedback_count, 2)
        self.assertAlmostEqual(report.service_feedback_sum, 9.0)
        self.assertAlmostEqual(report.avg_service_feedback, 4.5)
        self.assertEqual(report.min_service_feedback, 4)

    def test_null_avg_when_no_feedbacks(self):
        """avg_service_feedback is None when no feedback records exist in the period."""
        service = _make_service(feedbacks=[])
        service.handle_feedback_event(_make_feedback_event())
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertIsNone(report.avg_service_feedback)
        self.assertIsNone(report.min_service_feedback)

    def test_attributes_feedback_to_reservation_week_not_submission(self):
        """Feedback lands in the reservation's ISO week, not the submission week.

        The reservation dined in the week of 2026-06-01; the review is submitted
        the following week. The report must be upserted for the dining week so a
        single reservation's orders, revenue, and feedback stay together.
        """
        service = _make_service(feedbacks=[_make_feedback()])
        msg = _make_feedback_event()
        msg.timestamp = "2026-06-10T09:00:00Z"  # Wed of the following ISO week
        service.handle_feedback_event(msg)
        report: WaiterReport = service._waiter_report_repo.update.call_args.args[0]
        self.assertEqual(report.report_period_start, "2026-06-01")
        self.assertEqual(report.report_period_end, "2026-06-07")

"""Unit tests for LocationReportService report upsert logic."""

from datetime import UTC, datetime, time
from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.dish import Dish
    from domain.feedback import FeedbackCuisine
    from domain.location import Location
    from domain.location_report import LocationReport
    from domain.order import Order
    from domain.order_item import OrderItem
    from domain.reservation import Reservation
    from domain.user import Waiter
    from dto.feedback_event import FeedbackEventMessage, FeedbackEventType
    from dto.reservation_event import ReservationEventMessage, ReservationEventType
    from dto.reservation_management import AllowedActions
    from enums import FeedbackType, ReservationStatus
    from services.location_report_service import LocationReportService


# ── Fixtures ──────────────────────────────────────────────────────────────────

_LOCATION_ID = uuid4()
_WAITER_ID = uuid4()
_PERIOD_DATE = "2026-06-04"  # Wednesday → week Mon 2026-06-01 – Sun 2026-06-07


def _make_location() -> Location:
    """Return a Location domain object for tests."""
    return Location(
        id=_LOCATION_ID,
        name="Location 1",
        address="1 Main St",
        description="",
        image_url="",
        open_time=time(9, 0),
        close_time=time(22, 0),
    )


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


def _make_reservation(
    status: ReservationStatus = ReservationStatus.FINISHED,
) -> Reservation:
    """Return a minimal Reservation on _PERIOD_DATE."""
    return Reservation(
        id=uuid4(),
        customer_id=uuid4(),
        waiter_id=_WAITER_ID,
        created_at=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
        slot_ids=[uuid4()],
        status=status,
        number_of_guests=2,
        date="2026-06-04",
    )


def _make_order(reservation_id=None, dish_id=None, quantity: int = 1) -> Order:
    """Return a minimal Order for tests."""
    return Order(
        id=uuid4(),
        reservation_id=reservation_id or uuid4(),
        waiter_id=_WAITER_ID,
        items=[OrderItem(dish_id=dish_id or uuid4(), quantity=quantity)],
        created_at=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
    )


def _make_dish(price: float = 5.0) -> Dish:
    """Return a minimal Dish with the given price."""
    return Dish(
        id=uuid4(),
        location_id=_LOCATION_ID,
        name="Pasta",
        description="",
        image_url="",
        price=price,
        weight_gram=300,
    )


def _make_feedback(rate: int = 4) -> FeedbackCuisine:
    """Return a minimal FeedbackCuisine record."""
    return FeedbackCuisine(
        id=uuid4(),
        reservation_id=uuid4(),
        customer_id=uuid4(),
        feedback="Good",
        rate=rate,
        date=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        location_id=_LOCATION_ID,
    )


def _make_service(
    reservations=None,
    feedbacks=None,
    existing_report=None,
    prev_report=None,
    orders_per_reservation: int = 1,
    dish_price: float = 5.0,
) -> LocationReportService:
    """Build a LocationReportService with fully mocked repositories."""
    location_report_repo = MagicMock()
    location_report_repo.find_by_location_and_period.side_effect = lambda lid, ps: (
        prev_report if ps == "2026-05-25" else existing_report
    )

    location_repo = MagicMock()
    location_repo.get.return_value = _make_location()

    waiter_repo = MagicMock()
    waiter_repo.find_by_location_id.return_value = [_make_waiter()]

    reservation_repo = MagicMock()
    reservation_repo.find_by_waiter_id_and_period.return_value = reservations or []
    reservation_repo.get.return_value = _make_reservation()

    feedback_cuisine_repo = MagicMock()
    feedback_cuisine_repo.find_by_location_id_and_period.return_value = feedbacks or []

    order_repo = MagicMock()
    order_repo.find_by_reservation_id.side_effect = lambda rid: [
        _make_order(rid) for _ in range(orders_per_reservation)
    ]

    dish_repo = MagicMock()
    dish_repo.get.return_value = _make_dish(price=dish_price)

    return LocationReportService(
        location_report_repo=location_report_repo,
        location_repo=location_repo,
        waiter_repo=waiter_repo,
        reservation_repo=reservation_repo,
        feedback_cuisine_repo=feedback_cuisine_repo,
        order_repo=order_repo,
        dish_repo=dish_repo,
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
        date=_PERIOD_DATE,
        time_from="10:00",
        time_to="11:30",
        guests_number=2,
        allowed_actions=AllowedActions(can_edit=False, can_cancel=False),
    )


def _make_feedback_event(
    feedback_type: str = FeedbackType.CULINARY.value,
    rate: int = 4,
) -> FeedbackEventMessage:
    """Return a minimal FeedbackEventMessage."""
    return FeedbackEventMessage(
        event_type=FeedbackEventType.CREATED,
        feedback_id=str(uuid4()),
        reservation_id=str(uuid4()),
        customer_id=str(uuid4()),
        feedback="Tasty",
        rate=rate,
        date="2026-06-04T12:00:00Z",
        feedback_type=feedback_type,
        location_id=str(_LOCATION_ID),
        timestamp="2026-06-04T12:00:00Z",
    )


# ── Reservation event handling ────────────────────────────────────────────────


class TestHandleReservationEvent(TestCase):
    """Tests for LocationReportService.handle_reservation_event."""

    def test_skips_non_finished_events(self):
        """Non-FINISHED events do not trigger a report upsert."""
        service = _make_service()
        service.handle_reservation_event(
            _make_reservation_event(ReservationEventType.CREATED)
        )
        service._location_report_repo.update.assert_not_called()

    def test_skips_events_without_location_id(self):
        """Events with no location_id do not trigger a report upsert."""
        service = _make_service()
        msg = _make_reservation_event()
        msg.location_id = None
        service.handle_reservation_event(msg)
        service._location_report_repo.update.assert_not_called()

    def test_skips_when_location_not_found(self):
        """No upsert when the location does not exist in the database."""
        service = _make_service()
        service._location_repo.get.return_value = None
        service.handle_reservation_event(_make_reservation_event())
        service._location_report_repo.update.assert_not_called()

    def test_creates_new_report_on_first_event(self):
        """A new LocationReport row is created when none exists for the period."""
        service = _make_service(reservations=[_make_reservation()], dish_price=5.0)

        service.handle_reservation_event(_make_reservation_event())

        service._location_report_repo.update.assert_called_once()
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertEqual(str(report.location_id), str(_LOCATION_ID))
        self.assertEqual(report.report_period_start, "2026-06-01")
        self.assertEqual(report.report_period_end, "2026-06-07")
        self.assertEqual(report.orders_processed, 1)
        self.assertAlmostEqual(report.revenue, 5.0)

    def test_preserves_existing_report_id(self):
        """When a row already exists for the period, its id is preserved."""
        existing_id = uuid4()
        existing = LocationReport(
            id=existing_id,
            location_id=_LOCATION_ID,
            location_name="Location 1",
            report_period_start="2026-06-01",
            report_period_end="2026-06-07",
            orders_processed=1,
            cuisine_feedback_count=0,
            cuisine_feedback_sum=0.0,
        )
        service = _make_service(
            reservations=[_make_reservation()],
            existing_report=existing,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertEqual(report.id, existing_id)

    def test_counts_only_finished_reservations_for_orders(self):
        """orders_processed only counts FINISHED reservations."""
        finished = _make_reservation(ReservationStatus.FINISHED)
        cancelled = _make_reservation(ReservationStatus.CANCELLED)
        service = _make_service(reservations=[finished, cancelled])
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertEqual(report.orders_processed, 1)

    def test_calculates_delta_against_previous_period(self):
        """Delta percentage is computed from the previous ISO week's row."""
        prev = LocationReport(
            id=uuid4(),
            location_id=_LOCATION_ID,
            location_name="Location 1",
            report_period_start="2026-05-25",
            report_period_end="2026-05-31",
            orders_processed=10,
            cuisine_feedback_count=0,
            cuisine_feedback_sum=0.0,
            revenue=10.0,
        )
        service = _make_service(
            reservations=[_make_reservation()],
            prev_report=prev,
            dish_price=5.0,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertIsNotNone(report.orders_processed_delta_pct)
        self.assertAlmostEqual(report.orders_processed_delta_pct, -90.0)
        self.assertIsNotNone(report.revenue_delta_pct)
        self.assertAlmostEqual(report.revenue_delta_pct, -50.0)

    def test_no_delta_when_no_previous_period(self):
        """Delta is None when there is no previous period row."""
        service = _make_service(reservations=[_make_reservation()])
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertIsNone(report.orders_processed_delta_pct)


# ── Feedback event handling ───────────────────────────────────────────────────


class TestHandleFeedbackEvent(TestCase):
    """Tests for LocationReportService.handle_feedback_event."""

    def test_skips_service_feedback(self):
        """SERVICE feedback events do not trigger a location report upsert."""
        service = _make_service()
        service.handle_feedback_event(_make_feedback_event(FeedbackType.SERVICE.value))
        service._location_report_repo.update.assert_not_called()

    def test_skips_events_without_location_id(self):
        """Feedback events with no location_id do not trigger a report upsert."""
        service = _make_service()
        msg = _make_feedback_event()
        msg.location_id = None
        service.handle_feedback_event(msg)
        service._location_report_repo.update.assert_not_called()

    def test_stores_feedback_stats(self):
        """Feedback count, sum, avg, and min are computed from the DB query result."""
        feedbacks = [_make_feedback(rate=4), _make_feedback(rate=5)]
        service = _make_service(feedbacks=feedbacks)
        service.handle_feedback_event(_make_feedback_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertEqual(report.cuisine_feedback_count, 2)
        self.assertAlmostEqual(report.cuisine_feedback_sum, 9.0)
        self.assertAlmostEqual(report.avg_cuisine_feedback, 4.5)
        self.assertEqual(report.min_cuisine_feedback, 4)

    def test_null_avg_when_no_feedbacks(self):
        """avg_cuisine_feedback is None when no feedback records exist in the period."""
        service = _make_service(feedbacks=[])
        service.handle_feedback_event(_make_feedback_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertIsNone(report.avg_cuisine_feedback)
        self.assertIsNone(report.min_cuisine_feedback)

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
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertEqual(report.report_period_start, "2026-06-01")
        self.assertEqual(report.report_period_end, "2026-06-07")


# ── Revenue calculation ───────────────────────────────────────────────────────


class TestRevenueCalculation(TestCase):
    """Tests for revenue aggregation in LocationReportService."""

    def test_calculates_revenue_from_orders(self):
        """Revenue equals sum of (quantity × dish price) across all order items."""
        service = _make_service(
            reservations=[_make_reservation()],
            orders_per_reservation=2,
            dish_price=5.0,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertAlmostEqual(report.revenue, 10.0)

    def test_zero_revenue_when_no_orders(self):
        """Revenue is 0.0 when no Order records exist for the period."""
        service = _make_service(
            reservations=[_make_reservation()],
            orders_per_reservation=0,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertAlmostEqual(report.revenue, 0.0)
        self.assertIsNone(report.revenue_delta_pct)

    def test_revenue_delta_against_previous_period(self):
        """Revenue delta is computed as % change from the previous ISO week."""
        prev = LocationReport(
            id=uuid4(),
            location_id=_LOCATION_ID,
            location_name="Location 1",
            report_period_start="2026-05-25",
            report_period_end="2026-05-31",
            orders_processed=1,
            cuisine_feedback_count=0,
            cuisine_feedback_sum=0.0,
            revenue=4.0,
        )
        service = _make_service(
            reservations=[_make_reservation()],
            prev_report=prev,
            dish_price=5.0,
        )
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertAlmostEqual(report.revenue, 5.0)
        self.assertAlmostEqual(report.revenue_delta_pct, 25.0)

    def test_no_revenue_delta_when_no_previous_period(self):
        """revenue_delta_pct is None when there is no previous period row."""
        service = _make_service(reservations=[_make_reservation()])
        service.handle_reservation_event(_make_reservation_event())
        report: LocationReport = service._location_report_repo.update.call_args.args[0]
        self.assertIsNone(report.revenue_delta_pct)

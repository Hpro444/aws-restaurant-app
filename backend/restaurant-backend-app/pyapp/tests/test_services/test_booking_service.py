"""Service-level tests for BookingService slot chain and overbooking rules."""

import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from commons.exceptions import ApplicationException
from domain.location import Location
from domain.slot import Slot
from domain.table import Table
from domain.user import Customer, Waiter
from dto.create_booking import CreateBookingRequest
from dto.reservation_event import ReservationEventMessage, ReservationEventType
from enums import SlotStatus
from services.booking_service import BookingService


class DummySlotRepo:
    """Mock slot repository for testing."""

    def __init__(self, slots):
        """Initialize with list of slots."""
        self._slots = slots
        self._claimed = []

    def find_by_table_id_and_date(self, table_id, d):
        """Return mock slots for the given table and date."""
        return self._slots

    def update_status(self, slot_id, new_status, expected):
        """Update slot status if it matches expected status."""
        for s in self._slots:
            if s.id == slot_id and s.status == expected:
                s.status = new_status
                self._claimed.append(s)
                return True
        return False


class DummyTableRepo:
    """Mock table repository for testing."""

    def __init__(self, table):
        """Initialize with a single table."""
        self._table = table

    def find_by_location_id(self, location_id):
        """Return mock table for the given location."""
        return [self._table]


class DummyLocationRepo:
    """Mock location repository for testing."""

    def __init__(self, location):
        """Initialize with a single location."""
        self._location = location

    def get(self, location_id):
        """Return mock location."""
        return self._location


class DummyReservationRepo:
    """Mock reservation repository for testing."""

    def create(self, reservation):
        """Store and return the reservation."""
        self.last_created = reservation
        return reservation


class DummyWaiterRepo:
    """Mock waiter repository for testing waiter assignment."""

    def __init__(self, location_id):
        """Initialize with a fixed location id for generated waiter records."""
        self._location_id = location_id

    def find_by_location_id(self, location_id):
        """Return one deterministic waiter mapped to the configured location."""
        return [
            Waiter(
                id=uuid4(),
                fname="W",
                lname="One",
                email="w1@example.com",
                image_url="",
                location_id=self._location_id,
            )
        ]

    def get(self, waiter_id):
        """Return a deterministic waiter for any id."""
        return Waiter(
            id=waiter_id,
            fname="W",
            lname="One",
            email="w1@example.com",
            image_url="",
            location_id=self._location_id,
        )


class DummyCustomerRepo:
    """Mock customer repository for resolving client_name."""

    def get(self, customer_id):
        """Return synthetic customer profile for provided id."""
        return Customer(
            id=customer_id,
            fname="Ana",
            lname="Nikolic",
            email="ana@example.com",
            image_url="",
        )


class DummyWaiterViewRepo:
    """Mock waiter-dashboard projection repository for testing."""

    def __init__(self):
        """Track upserts and deletes for assertions."""
        self.upserted = []
        self.deleted = []

    def update(self, view):
        """Record a projection upsert."""
        self.upserted.append(view)

    def delete(self, item_id):
        """Record a projection delete."""
        self.deleted.append(item_id)


def make_slot(start, status=SlotStatus.FREE, days_offset=1):
    """Create a test Slot with timezone-aware datetime.

    By default slots are generated for tomorrow so tests are stable regardless
    of the current UTC hour.
    """
    slot_day = date.today() + timedelta(days=days_offset)
    dt = datetime.combine(slot_day, time(hour=start, minute=0, tzinfo=timezone.utc))
    slot_date = datetime.combine(slot_day, time.min, tzinfo=timezone.utc)
    return Slot(
        id=uuid4(),
        table_id=uuid4(),
        waiter_id=uuid4(),
        start_time=dt,
        end_time=dt + timedelta(minutes=90),
        status=status,
        date=slot_date,
    )


def _build_service():
    """Build a BookingService with all dummy repositories wired up."""
    table = Table(id=uuid4(), location_id=uuid4(), table_number=1, capacity=6)
    location = Location(
        id=table.location_id,
        name="48 Rustaveli Avenue, Tbilisi",
        address="48 Rustaveli Avenue, Tbilisi",
        description="Test Description",
        image_url="http://test.com/image.jpg",
        open_time=time(10, 0),
        close_time=time(22, 0),
    )
    service = BookingService()
    service._table_repo = DummyTableRepo(table)
    service._slot_repo = None
    service._reservation_repo = DummyReservationRepo()
    service._location_repo = DummyLocationRepo(location)
    service._customer_repo = DummyCustomerRepo()
    service._waiter_repo = DummyWaiterRepo(table.location_id)
    service._waiter_view_repo = DummyWaiterViewRepo()
    return service, table, location


class TestBookingService(unittest.TestCase):
    """Tests for BookingService slot chain and overbooking rules."""

    def setUp(self):
        """Set up service with dummy repositories before each test."""
        self.service, self.table, self.location = _build_service()

    @staticmethod
    def _utc(dt: datetime) -> str:
        """Format datetime as UTC ISO string expected by booking DTO."""
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def test_single_slot_booking_success(self):
        """Test successful booking of a single 90-minute slot."""
        slot = make_slot(12)
        self.service._slot_repo = DummySlotRepo([slot])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot.start_time),
            time_to=self._utc(slot.end_time),
        )
        resp = self.service.create_booking(req, uuid4())
        self.assertEqual(resp.status, "Reserved")
        self.assertIsNotNone(self.service._reservation_repo.last_created.waiter_id)
        self.assertEqual(
            self.service._reservation_repo.last_created.client_name, "Ana Nikolic"
        )
        self.assertEqual(resp.client_name, "Ana Nikolic")

    def test_waiter_visitor_booking_persists_without_customer_id(self):
        """Visitor flow stores customer_id=None and waiter is derived from slot[0]."""
        slot = make_slot(12)
        self.service._slot_repo = DummySlotRepo([slot])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot.start_time),
            time_to=self._utc(slot.end_time),
        )

        resp = self.service.create_booking(
            req, None, client_name="Petar Petrovic", waiter_id=uuid4()
        )

        self.assertEqual(resp.status, "Reserved")
        self.assertIsNone(self.service._reservation_repo.last_created.customer_id)
        self.assertEqual(
            self.service._reservation_repo.last_created.client_name, "Petar Petrovic"
        )
        self.assertEqual(
            self.service._reservation_repo.last_created.waiter_id, slot.waiter_id
        )
        self.assertEqual(resp.client_name, "Petar Petrovic")

    def test_single_slot_booking_writes_projection(self):
        """A successful booking upserts a waiter-view row keyed by the reservation id."""
        slot = make_slot(12)
        self.service._slot_repo = DummySlotRepo([slot])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot.start_time),
            time_to=self._utc(slot.end_time),
        )

        resp = self.service.create_booking(req, uuid4())

        self.assertEqual(len(self.service._waiter_view_repo.upserted), 1)
        view = self.service._waiter_view_repo.upserted[0]
        self.assertEqual(str(view.id), resp.reservation_id)
        self.assertEqual(view.table_number, self.table.table_number)
        self.assertEqual(view.table_name, str(self.table.table_number))
        self.assertEqual(view.location_address, self.location.address)
        self.assertEqual(view.date, slot.start_time.date().isoformat())
        self.assertEqual(view.time_from, slot.start_time.strftime("%H:%M"))

    def test_multi_slot_chain_success(self):
        """Test successful booking of multiple slots with a 15-minute pause (195 minutes)."""
        slot1 = make_slot(12)
        slot2 = make_slot(13, status=SlotStatus.FREE)
        slot2.start_time = slot1.end_time + timedelta(minutes=15)
        slot2.end_time = slot2.start_time + timedelta(minutes=90)
        self.service._slot_repo = DummySlotRepo([slot1, slot2])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot2.end_time),
        )
        resp = self.service.create_booking(req, uuid4())
        self.assertEqual(resp.status, "Reserved")

    def test_slot_chain_with_gap_fails(self):
        """Test that non-contiguous slot chain is rejected."""
        slot1 = make_slot(12)
        slot2 = make_slot(14)
        self.service._slot_repo = DummySlotRepo([slot1, slot2])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot2.end_time),
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.create_booking(req, uuid4())
        self.assertIn("Invalid time range", str(ctx.exception))

    def test_slot_chain_with_reserved_slot_fails(self):
        """Test that booking fails if any slot in chain is already reserved."""
        slot1 = make_slot(12)
        slot2 = make_slot(13, status=SlotStatus.RESERVED)
        slot2.start_time = slot1.end_time + timedelta(minutes=15)
        slot2.end_time = slot2.start_time + timedelta(minutes=90)
        self.service._slot_repo = DummySlotRepo([slot1, slot2])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot2.end_time),
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.create_booking(req, uuid4())
        self.assertIn("already reserved", str(ctx.exception))

    def test_slot_chain_exceeds_closing_time_fails(self):
        """Test that booking fails if it extends past location's closing time."""
        slot1 = make_slot(21)
        self.service._slot_repo = DummySlotRepo([slot1])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot1.end_time),
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.create_booking(req, uuid4())
        self.assertIn("beyond location closing time", str(ctx.exception))

    def test_booking_start_in_past_fails(self):
        """Test that booking is rejected when the selected start time is in the past."""
        slot = make_slot(10, days_offset=0)
        self.service._slot_repo = DummySlotRepo([slot])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot.start_time),
            time_to=self._utc(slot.end_time),
        )

        fixed_now = datetime.combine(date.today(), time(11, 0), tzinfo=timezone.utc)
        with patch("services.booking_service.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = fixed_now
            mocked_datetime.fromisoformat = datetime.fromisoformat
            with self.assertRaises(ApplicationException) as ctx:
                self.service.create_booking(req, uuid4())

        self.assertEqual(ctx.exception.code, 422)
        self.assertIn("starts in the past", str(ctx.exception))

    def test_slot_with_non_90_min_duration_fails(self):
        """Test that chain is rejected when any selected slot is not 90 minutes long."""
        slot1 = make_slot(12)
        slot1.end_time = slot1.start_time + timedelta(minutes=75)
        self.service._slot_repo = DummySlotRepo([slot1])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot1.end_time),
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.create_booking(req, uuid4())
        self.assertIn("Invalid time range", str(ctx.exception))

    def test_edit_cancel_cutoff_enforced(self):
        """Test that edit/cancel are disabled 30 minutes before reservation start time."""
        import services.reservation_management_service as mgmt_mod
        from dto.reservation_management import UpdateReservationRequest
        from enums import ReservationStatus, UserRole
        from services.reservation_management_service import ReservationManagementService

        slot = make_slot(12)
        now = slot.start_time - timedelta(minutes=25)

        class FakeDateTime:
            """Fake datetime that returns a fixed 'now'."""

            @staticmethod
            def now(tz=None):
                """Return fixed now."""
                return now

        customer_id = uuid4()
        reservation = type("Res", (), {})()
        reservation.id = uuid4()
        reservation.customer_id = customer_id
        reservation.waiter_id = uuid4()
        reservation.created_at = slot.start_time - timedelta(hours=1)
        reservation.slot_ids = [slot.id]
        reservation.status = ReservationStatus.RESERVED
        reservation.number_of_guests = 2

        class _DummySlotRepo:
            """Slot repo for cutoff test."""

            def find_by_ids(self, ids):
                """Return test slot."""
                return [slot]

            def update_status(self, *a, **kw):
                """No-op update."""
                return True

        class _DummyReservationRepo:
            """Reservation repo for cutoff test."""

            def get(self, rid):
                """Return test reservation."""
                return reservation

            def update(self, r):
                """No-op update."""

        class _DummyTableRepo:
            """Table repo for cutoff test."""

            def get(self, tid):
                """Return test table."""
                return self.service.table  # not used in cutoff check

        mgmt = ReservationManagementService()
        mgmt._reservation_repo = _DummyReservationRepo()
        mgmt._slot_repo = _DummySlotRepo()
        mgmt._table_repo = _DummyTableRepo()

        req = UpdateReservationRequest(guests_number=3, status=None)
        with patch.object(mgmt_mod, "datetime", FakeDateTime):
            with self.assertRaises(Exception) as ctx:
                mgmt.update_reservation(
                    reservation.id,
                    req,
                    customer_id,
                    UserRole.CUSTOMER,
                )
        self.assertIn("disabled 30 minutes before start", str(ctx.exception))

    def test_multi_slot_chain_duration_formula(self):
        """Test that multi-slot booking must match 90*n + 15*(n-1) duration."""
        slot1 = make_slot(12)
        slot2 = make_slot(13)
        slot2.start_time = slot1.end_time + timedelta(minutes=15)
        slot2.end_time = slot2.start_time + timedelta(minutes=90)
        self.service._slot_repo = DummySlotRepo([slot1, slot2])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot2.end_time),
        )
        resp = self.service.create_booking(req, uuid4())
        self.assertEqual(resp.status, "Reserved")

    def test_multi_slot_chain_invalid_duration_fails(self):
        """Test that booking fails if total duration doesn't match formula."""
        slot1 = make_slot(12)
        slot2 = make_slot(13)
        slot2.start_time = slot1.end_time + timedelta(minutes=10)
        slot2.end_time = slot2.start_time + timedelta(minutes=90)
        self.service._slot_repo = DummySlotRepo([slot1, slot2])
        req = CreateBookingRequest(
            location_id=self.table.location_id,
            table_number=1,
            date=slot1.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot1.start_time),
            time_to=self._utc(slot2.end_time),
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.create_booking(req, uuid4())
        self.assertIn("Invalid time range", str(ctx.exception))


class TestBookingServiceSqsPublishing(unittest.TestCase):
    """Tests verifying SQS event publishing on successful bookings."""

    @staticmethod
    def _utc(dt: datetime) -> str:
        """Format datetime as UTC ISO string expected by booking DTO."""
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _make_request_and_slot(self, table):
        """Return a matching (CreateBookingRequest, Slot) pair."""
        slot = make_slot(12)
        slot.table_id = table.id
        req = CreateBookingRequest(
            location_id=table.location_id,
            table_number=1,
            date=slot.start_time.date().isoformat(),
            guests_number=2,
            time_from=self._utc(slot.start_time),
            time_to=self._utc(slot.end_time),
        )
        return req, slot

    def test_sqs_publish_called_once_on_successful_booking(self):
        """SqsService.publish is called exactly once after a successful booking."""
        service, table, _ = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs
        req, slot = self._make_request_and_slot(table)
        service._slot_repo = DummySlotRepo([slot])

        service.create_booking(req, uuid4())

        mock_sqs.publish.assert_called_once()

    def test_sqs_publish_event_type_is_created(self):
        """The message passed to SqsService.publish has event_type CREATED."""
        service, table, _ = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs
        req, slot = self._make_request_and_slot(table)
        service._slot_repo = DummySlotRepo([slot])

        service.create_booking(req, uuid4())

        message = mock_sqs.publish.call_args.args[1]
        self.assertIsInstance(message, ReservationEventMessage)
        self.assertEqual(message.event_type, ReservationEventType.CREATED)

    def test_sqs_publish_view_contains_reservation_id(self):
        """The ReservationView inside the message has a non-empty reservation_id."""
        service, table, _ = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs
        req, slot = self._make_request_and_slot(table)
        service._slot_repo = DummySlotRepo([slot])

        resp = service.create_booking(req, uuid4())

        message = mock_sqs.publish.call_args.args[1]
        self.assertEqual(message.reservation_id, resp.reservation_id)

    def test_sqs_not_called_when_booking_fails(self):
        """SqsService.publish is not called when the reservation repo raises."""
        service, table, _ = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs

        failing_repo = MagicMock()
        failing_repo.create.side_effect = ApplicationException(409, "conflict")
        service._reservation_repo = failing_repo

        req, slot = self._make_request_and_slot(table)
        service._slot_repo = DummySlotRepo([slot])

        with self.assertRaises(ApplicationException):
            service.create_booking(req, uuid4())

        mock_sqs.publish.assert_not_called()

    def test_sqs_none_does_not_raise(self):
        """create_booking completes normally when sqs_service is None."""
        service, table, _ = _build_service()
        service._sqs = None
        req, slot = self._make_request_and_slot(table)
        service._slot_repo = DummySlotRepo([slot])

        resp = service.create_booking(req, uuid4())

        self.assertEqual(resp.status, "Reserved")


if __name__ == "__main__":
    unittest.main()

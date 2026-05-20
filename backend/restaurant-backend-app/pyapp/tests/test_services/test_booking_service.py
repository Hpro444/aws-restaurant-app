"""Service-level tests for BookingService slot chain and overbooking rules."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

import pytest
from commons.exceptions import ApplicationException
from domain.location import Location
from domain.slot import Slot
from domain.table import Table
from domain.user import Waiter
from dto.create_booking import CreateBookingRequest
from enums.slot_status import SlotStatus
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


@pytest.fixture
def booking_service():
    """Provide BookingService with mocked repositories for testing."""
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
    service._slot_repo = None  # set per test
    service._reservation_repo = DummyReservationRepo()
    service._location_repo = DummyLocationRepo(location)
    service._waiter_repo = DummyWaiterRepo(table.location_id)
    return service, table, location


def make_slot(start, status=SlotStatus.FREE):
    """Create a test Slot with timezone-aware datetime."""
    dt = datetime.combine(date.today(), time(hour=start, minute=0, tzinfo=timezone.utc))
    slot_date = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    return Slot(
        id=uuid4(),
        table_id=uuid4(),
        start_time=dt,
        end_time=dt + timedelta(minutes=90),
        status=status,
        date=slot_date,
    )


def test_single_slot_booking_success(booking_service):
    """Test successful booking of a single 90-minute slot."""
    service, table, location = booking_service
    slot = make_slot(12)
    service._slot_repo = DummySlotRepo([slot])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot.start_time.strftime("%H:%M"),
        time_to=slot.end_time.strftime("%H:%M"),
    )
    resp = service.create_booking(req, uuid4())
    assert resp.status == "RESERVED"
    assert service._reservation_repo.last_created.waiter_id is not None


def test_multi_slot_chain_success(booking_service):
    """Test successful booking of multiple slots with a 15-minute pause (195 minutes)."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot2 = make_slot(13, status=SlotStatus.FREE)
    slot2.start_time = slot1.end_time + timedelta(minutes=15)
    slot2.end_time = slot2.start_time + timedelta(minutes=90)
    service._slot_repo = DummySlotRepo([slot1, slot2])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot2.end_time.strftime("%H:%M"),
    )
    resp = service.create_booking(req, uuid4())
    assert resp.status == "RESERVED"


def test_slot_chain_with_gap_fails(booking_service):
    """Test that non-contiguous slot chain is rejected."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot2 = make_slot(14)  # gap!
    service._slot_repo = DummySlotRepo([slot1, slot2])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot2.end_time.strftime("%H:%M"),
    )
    with pytest.raises(ApplicationException) as exc:
        service.create_booking(req, uuid4())
    assert "Invalid time range" in str(exc.value)


def test_slot_chain_with_reserved_slot_fails(booking_service):
    """Test that booking fails if any slot in chain is already reserved."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot2 = make_slot(13, status=SlotStatus.RESERVED)
    slot2.start_time = slot1.end_time + timedelta(minutes=15)
    slot2.end_time = slot2.start_time + timedelta(minutes=90)
    service._slot_repo = DummySlotRepo([slot1, slot2])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot2.end_time.strftime("%H:%M"),
    )
    with pytest.raises(ApplicationException) as exc:
        service.create_booking(req, uuid4())
    assert "already reserved" in str(exc.value)


def test_slot_chain_exceeds_closing_time_fails(booking_service):
    """Test that booking fails if it extends past location's closing time."""
    service, table, location = booking_service
    # location.close_time is 22:00, create a slot that ends after that
    slot1 = make_slot(21)  # 21:00 - 22:30, extends past close_time
    service._slot_repo = DummySlotRepo([slot1])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot1.end_time.strftime("%H:%M"),
    )
    with pytest.raises(ApplicationException) as exc:
        service.create_booking(req, uuid4())
    assert "beyond location closing time" in str(exc.value)


def test_slot_with_non_90_min_duration_fails(booking_service):
    """Test that chain is rejected when any selected slot is not 90 minutes long."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot1.end_time = slot1.start_time + timedelta(minutes=75)
    service._slot_repo = DummySlotRepo([slot1])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot1.end_time.strftime("%H:%M"),
    )

    with pytest.raises(ApplicationException) as exc:
        service.create_booking(req, uuid4())

    assert "Invalid time range" in str(exc.value)


def test_edit_cancel_cutoff_enforced(monkeypatch, booking_service):
    """Test that edit/cancel are disabled 30 minutes before reservation start time."""
    import services.reservation_management_service as mgmt_mod
    from dto.reservation_management import UpdateReservationRequest
    from enums.reservation_status import ReservationStatus
    from enums.user_role import UserRole
    from services.reservation_management_service import ReservationManagementService

    service, table, location = booking_service
    slot = make_slot(12)
    # Rezervacija počinje za manje od 30 minuta
    now = slot.start_time - timedelta(minutes=25)

    # Patch datetime.now to simulate current time
    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            return now

    monkeypatch.setattr(mgmt_mod, "datetime", FakeDateTime)
    # Kreiraj rezervaciju sa istim korisnikom kao actor
    customer_id = uuid4()
    reservation = type("Res", (), {})()
    reservation.id = uuid4()
    reservation.customer_id = customer_id
    reservation.waiter_id = uuid4()
    reservation.created_at = slot.start_time - timedelta(hours=1)
    reservation.slot_ids = [slot.id]
    reservation.status = ReservationStatus.RESERVED
    reservation.number_of_guests = 2

    # Dummy slot repo
    class DummySlotRepo:
        def find_by_ids(self, ids):
            return [slot]

        def update_status(self, *a, **kw):
            return True

    # Dummy reservation repo
    class DummyReservationRepo:
        def get(self, rid):
            return reservation

        def update(self, r):
            pass

    # Dummy table repo
    class DummyTableRepo:
        def get(self, tid):
            return table

    mgmt = ReservationManagementService()
    mgmt._reservation_repo = DummyReservationRepo()
    mgmt._slot_repo = DummySlotRepo()
    mgmt._table_repo = DummyTableRepo()
    # Pokušaj izmene
    req = UpdateReservationRequest(guests_number=3, status=None)
    with pytest.raises(Exception) as exc:
        mgmt.update_reservation(
            reservation.id,
            req,
            customer_id,
            UserRole.CUSTOMER.value,
        )
    assert "disabled 30 minutes before start" in str(exc.value)


def test_multi_slot_chain_duration_formula(booking_service):
    """Test that multi-slot booking must match 90*n + 15*(n-1) duration."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot2 = make_slot(13)
    # slot2 počinje 15 min nakon kraja slot1
    slot2.start_time = slot1.end_time + timedelta(minutes=15)
    slot2.end_time = slot2.start_time + timedelta(minutes=90)
    service._slot_repo = DummySlotRepo([slot1, slot2])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot2.end_time.strftime("%H:%M"),
    )
    resp = service.create_booking(req, uuid4())
    assert resp.status == "RESERVED"


def test_multi_slot_chain_invalid_duration_fails(booking_service):
    """Test that booking fails if total duration doesn't match formula."""
    service, table, location = booking_service
    slot1 = make_slot(12)
    slot2 = make_slot(13)
    # slot2 počinje 10 min nakon kraja slot1 (nevalidan gap)
    slot2.start_time = slot1.end_time + timedelta(minutes=10)
    slot2.end_time = slot2.start_time + timedelta(minutes=90)
    service._slot_repo = DummySlotRepo([slot1, slot2])
    req = CreateBookingRequest(
        location_id=table.location_id,
        table_number=1,
        date=date.today().isoformat(),
        guests_number=2,
        time_from=slot1.start_time.strftime("%H:%M"),
        time_to=slot2.end_time.strftime("%H:%M"),
    )
    with pytest.raises(ApplicationException) as exc:
        service.create_booking(req, uuid4())
    assert "Invalid time range" in str(exc.value)

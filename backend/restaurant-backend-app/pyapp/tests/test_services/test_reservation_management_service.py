"""Service-level tests for ReservationManagementService rules."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from commons.exceptions import ApplicationException
from domain.location import Location
from domain.reservation import Reservation
from domain.slot import Slot
from domain.table import Table
from dto.reservation_management import UpdateReservationRequest
from enums.reservation_status import ReservationStatus
from enums.slot_status import SlotStatus
from enums.user_role import UserRole
from services.reservation_management_service import ReservationManagementService


class DummyReservationRepo:
    """In-memory reservation repository for testing."""

    def __init__(self, reservation):
        """Initialise with a single reservation."""
        self._reservation = reservation

    def get(self, item_id):
        """Return reservation if id matches."""
        return self._reservation if self._reservation.id == item_id else None

    def update(self, reservation):
        """Replace stored reservation."""
        self._reservation = reservation

    def find_by_customer_id(self, customer_id):
        """Return reservation list for customer."""
        return (
            [self._reservation] if self._reservation.customer_id == customer_id else []
        )

    def find_by_waiter_id(self, waiter_id):
        """Return reservation list for waiter."""
        return [self._reservation] if self._reservation.waiter_id == waiter_id else []


class DummySlotRepo:
    """In-memory slot repository for testing."""

    def __init__(self, slots):
        """Initialise with slot list."""
        self._slots = {slot.id: slot for slot in slots}

    def find_by_ids(self, slot_ids):
        """Return slots matching given ids."""
        return [self._slots[sid] for sid in slot_ids if sid in self._slots]

    def update_status(self, slot_id, new_status, expected):
        """Update slot status if expected status matches."""
        slot = self._slots[slot_id]
        if slot.status != expected:
            return False
        slot.status = new_status
        return True


class DummyTableRepo:
    """In-memory table repository for testing."""

    def __init__(self, table):
        """Initialise with a single table."""
        self._table = table

    def get(self, table_id):
        """Return table if id matches."""
        return self._table if self._table.id == table_id else None


class DummyLocationRepo:
    """In-memory location repository for testing."""

    def __init__(self, location):
        """Initialise with a single location."""
        self._location = location

    def get(self, location_id):
        """Return location if id matches."""
        return self._location if self._location.id == location_id else None


def _build_service(start_in_minutes=120):
    """Construct service with deterministic in-memory entities."""
    customer_id = uuid4()
    waiter_id = uuid4()
    location_id = uuid4()
    table_id = uuid4()
    slot_id = uuid4()

    start_time = datetime.now(UTC) + timedelta(minutes=start_in_minutes)
    end_time = start_time + timedelta(minutes=90)

    reservation = Reservation(
        id=uuid4(),
        customer_id=customer_id,
        waiter_id=waiter_id,
        created_at=datetime.now(UTC),
        slot_ids=[slot_id],
        status=ReservationStatus.RESERVED,
        number_of_guests=4,
    )
    slot = Slot(
        id=slot_id,
        table_id=table_id,
        start_time=start_time,
        end_time=end_time,
        date=start_time,
        status=SlotStatus.RESERVED,
    )
    table = Table(
        id=table_id,
        table_number=7,
        capacity=8,
        location_id=location_id,
    )
    location = Location(
        id=location_id,
        name="48 Rustaveli Avenue, Tbilisi",
        address="48 Rustaveli Avenue, Tbilisi",
        description="Test location",
        image_url="https://example.com/location.jpg",
        open_time=datetime.now(UTC).time(),
        close_time=datetime.now(UTC).time(),
    )

    service = ReservationManagementService()
    service._reservation_repo = DummyReservationRepo(reservation)
    service._slot_repo = DummySlotRepo([slot])
    service._table_repo = DummyTableRepo(table)
    service._location_repo = DummyLocationRepo(location)
    return service, reservation, customer_id, waiter_id


def test_customer_can_list_dashboard_reservations():
    """Customer should get own reservations in dashboard response."""
    service, reservation, customer_id, _ = _build_service()

    response = service.list_for_dashboard(customer_id, UserRole.CUSTOMER.value)

    assert len(response.reservations) == 1
    dashboard_item = response.reservations[0]
    assert dashboard_item.reservation_id == str(reservation.id)
    assert dashboard_item.status == ReservationStatus.RESERVED.value
    assert dashboard_item.location_name == "48 Rustaveli Avenue, Tbilisi"
    assert dashboard_item.date
    assert dashboard_item.time_from
    assert dashboard_item.time_to
    assert dashboard_item.guests_number == 4


def test_cancel_fails_within_cutoff_window():
    """Cancel is blocked when reservation starts within 30 minutes."""
    service, reservation, customer_id, _ = _build_service(start_in_minutes=20)

    with pytest.raises(ApplicationException) as exc:
        service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER.value,
        )

    assert exc.value.code == 422


def test_cancel_sets_status_cancelled_and_releases_slot():
    """Successful cancel updates reservation status and frees reserved slots."""
    service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

    response = service.cancel_reservation(
        reservation_id=reservation.id,
        actor_id=customer_id,
        role=UserRole.CUSTOMER.value,
    )

    assert response.status == ReservationStatus.CANCELLED.value


def test_assigned_waiter_can_progress_status_to_finished():
    """Assigned waiter can move reservation RESERVED->IN_PROGRESS->FINISHED."""
    service, reservation, _, waiter_id = _build_service(start_in_minutes=120)

    in_progress = service.update_reservation(
        reservation_id=reservation.id,
        request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
        actor_id=waiter_id,
        role=UserRole.WAITER.value,
    )
    assert in_progress.status == ReservationStatus.IN_PROGRESS.value

    finished = service.update_reservation(
        reservation_id=reservation.id,
        request=UpdateReservationRequest(status=ReservationStatus.FINISHED),
        actor_id=waiter_id,
        role=UserRole.WAITER.value,
    )
    assert finished.status == ReservationStatus.FINISHED.value


def test_customer_cannot_set_in_progress_status():
    """Customer must not be allowed to run waiter-only status transitions."""
    service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

    with pytest.raises(ApplicationException) as exc:
        service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
            actor_id=customer_id,
            role=UserRole.CUSTOMER.value,
        )

    assert exc.value.code == 403

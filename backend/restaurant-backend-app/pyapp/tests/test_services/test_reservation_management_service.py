"""Service-level tests for ReservationManagementService rules."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException
    from domain.location import Location
    from domain.reservation import Reservation
    from domain.reservation_waiter_view import ReservationWaiterView
    from domain.slot import Slot
    from domain.table import Table
    from domain.user import Waiter
    from dto.reservation_event import ReservationEventMessage, ReservationEventType
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


class DummyWaiterViewRepo:
    """In-memory waiter-dashboard projection repository for testing."""

    def __init__(self, rows=None):
        """Track writes and serve configured query rows."""
        self.upserted = []
        self.deleted = []
        self._rows = rows or []

    def update(self, view):
        """Record a projection upsert."""
        self.upserted.append(view)

    def delete(self, item_id):
        """Record a projection delete."""
        self.deleted.append(item_id)

    def query_for_table(self, location_id, date, time_from, table_name, waiter_id):
        """Return the configured projection rows, recording the queried waiter_id."""
        self.last_waiter_id = waiter_id
        return list(self._rows)


class DummyWaiterRepo:
    """In-memory waiter repository for testing."""

    def __init__(self, waiter=None):
        """Initialise with an optional waiter profile."""
        self._waiter = waiter

    def get(self, waiter_id):
        """Return the configured waiter profile (ignores the id)."""
        return self._waiter


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

    waiter = Waiter(
        id=waiter_id,
        fname="W",
        lname="One",
        email="w1@example.com",
        image_url="",
        location_id=location_id,
    )

    service = ReservationManagementService()
    service._reservation_repo = DummyReservationRepo(reservation)
    service._slot_repo = DummySlotRepo([slot])
    service._table_repo = DummyTableRepo(table)
    service._location_repo = DummyLocationRepo(location)
    service._waiter_repo = DummyWaiterRepo(waiter)
    service._waiter_view_repo = DummyWaiterViewRepo()
    return service, reservation, customer_id, waiter_id


class TestReservationManagementService(unittest.TestCase):
    """Tests for ReservationManagementService cancel/update business rules."""

    def test_customer_can_list_dashboard_reservations(self):
        """Customer should get own reservations in dashboard response."""
        service, reservation, customer_id, _ = _build_service()

        response = service.list_for_dashboard(customer_id, UserRole.CUSTOMER)

        self.assertEqual(len(response.reservations), 1)
        item = response.reservations[0]
        self.assertEqual(item.reservation_id, str(reservation.id))
        self.assertEqual(item.status, ReservationStatus.RESERVED)
        self.assertEqual(item.location_address, "48 Rustaveli Avenue, Tbilisi")
        self.assertTrue(item.date)
        self.assertTrue(item.time_from)
        self.assertTrue(item.time_to)
        self.assertEqual(item.guests_number, 4)

    def test_cancel_fails_within_cutoff_window(self):
        """Cancel is blocked when reservation starts within 30 minutes."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=20)

        with self.assertRaises(ApplicationException) as ctx:
            service.cancel_reservation(
                reservation_id=reservation.id,
                actor_id=customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 422)

    def test_cancel_sets_status_cancelled_and_releases_slot(self):
        """Successful cancel updates reservation status and frees reserved slots."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

        response = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(response.status, ReservationStatus.CANCELLED)

    def test_assigned_waiter_can_progress_status_to_finished(self):
        """Assigned waiter can move reservation RESERVED->IN_PROGRESS->FINISHED."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=120)

        in_progress = service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )
        self.assertEqual(in_progress.status, ReservationStatus.IN_PROGRESS)

        finished = service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.FINISHED),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )
        self.assertEqual(finished.status, ReservationStatus.FINISHED)

    def test_unassigned_waiter_cannot_update_reservation(self):
        """A waiter who is not assigned to the reservation cannot edit it."""
        service, reservation, _, _ = _build_service(start_in_minutes=120)
        other_waiter_id = uuid4()

        with self.assertRaises(ApplicationException) as ctx:
            service.update_reservation(
                reservation_id=reservation.id,
                request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
                actor_id=other_waiter_id,
                role=UserRole.WAITER,
            )

        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(
            ctx.exception.content["message"],
            "You are not allowed to access this reservation",
        )

    def test_customer_cannot_set_guests_above_table_capacity(self):
        """Customer edit is rejected when requested guests exceed table capacity."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

        with self.assertRaises(ApplicationException) as ctx:
            service.update_reservation(
                reservation_id=reservation.id,
                request=UpdateReservationRequest(guests_number=9),
                actor_id=customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 422)
        self.assertEqual(
            ctx.exception.content[0]["message"],
            "Guests number exceeds table capacity (8)",
        )
        self.assertEqual(reservation.number_of_guests, 4)

    def test_assigned_waiter_cannot_set_guests_above_table_capacity(self):
        """Assigned waiter edit is rejected when requested guests exceed capacity."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=120)

        with self.assertRaises(ApplicationException) as ctx:
            service.update_reservation(
                reservation_id=reservation.id,
                request=UpdateReservationRequest(guests_number=9),
                actor_id=waiter_id,
                role=UserRole.WAITER,
            )

        self.assertEqual(ctx.exception.code, 422)
        self.assertEqual(
            ctx.exception.content[0]["message"],
            "Guests number exceeds table capacity (8)",
        )
        self.assertEqual(reservation.number_of_guests, 4)

    def test_customer_cannot_set_in_progress_status(self):
        """Customer must not be allowed to run waiter-only status transitions."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

        with self.assertRaises(ApplicationException) as ctx:
            service.update_reservation(
                reservation_id=reservation.id,
                request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
                actor_id=customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 403)

    def test_assigned_waiter_can_cancel(self):
        """Assigned waiter is permitted to cancel the reservation before cutoff."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=120)

        response = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        self.assertEqual(response.status, ReservationStatus.CANCELLED)

    def test_assigned_waiter_can_update_guests_within_cutoff(self):
        """Assigned waiter can edit guests number even inside cutoff window."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=20)

        response = service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(guests_number=6),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        self.assertEqual(response.guests_number, 6)

    def test_assigned_waiter_can_cancel_within_cutoff(self):
        """Assigned waiter can cancel even when start is within customer cutoff window."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=20)

        response = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        self.assertEqual(response.status, ReservationStatus.CANCELLED)

    def test_unrelated_customer_cannot_cancel(self):
        """A customer who does not own the reservation receives 403."""
        service, reservation, _, _ = _build_service(start_in_minutes=120)
        other_customer_id = uuid4()

        with self.assertRaises(ApplicationException) as ctx:
            service.cancel_reservation(
                reservation_id=reservation.id,
                actor_id=other_customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 403)

    def test_cancel_already_cancelled_reservation_raises_422(self):
        """Cancelling a reservation that is already CANCELLED raises 422."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=120)
        reservation.status = ReservationStatus.CANCELLED

        with self.assertRaises(ApplicationException) as ctx:
            service.cancel_reservation(
                reservation_id=reservation.id,
                actor_id=customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 422)

    def test_cancel_29_minutes_before_start_raises_422(self):
        """Cancel at 29 minutes before start is inside the 30-minute cutoff window."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=29)

        with self.assertRaises(ApplicationException) as ctx:
            service.cancel_reservation(
                reservation_id=reservation.id,
                actor_id=customer_id,
                role=UserRole.CUSTOMER,
            )

        self.assertEqual(ctx.exception.code, 422)

    def test_cancel_31_minutes_before_start_succeeds(self):
        """Cancel at 31 minutes before start is just outside the cutoff window."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=31)

        response = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(response.status, ReservationStatus.CANCELLED)

    def test_cancel_releases_all_slots_in_multi_slot_reservation(self):
        """Every slot in a multi-slot reservation is set to FREE on cancellation."""
        customer_id = uuid4()
        waiter_id = uuid4()
        location_id = uuid4()
        table_id = uuid4()
        slot_id_1, slot_id_2 = uuid4(), uuid4()

        start_time = datetime.now(UTC) + timedelta(minutes=120)
        boundary = start_time + timedelta(minutes=90)
        end_time = boundary + timedelta(minutes=90)

        reservation = Reservation(
            id=uuid4(),
            customer_id=customer_id,
            waiter_id=waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[slot_id_1, slot_id_2],
            status=ReservationStatus.RESERVED,
            number_of_guests=4,
        )
        slot1 = Slot(
            id=slot_id_1,
            table_id=table_id,
            start_time=start_time,
            end_time=boundary,
            date=start_time,
            status=SlotStatus.RESERVED,
        )
        slot2 = Slot(
            id=slot_id_2,
            table_id=table_id,
            start_time=boundary,
            end_time=end_time,
            date=boundary,
            status=SlotStatus.RESERVED,
        )
        table = Table(id=table_id, table_number=3, capacity=4, location_id=location_id)
        location = Location(
            id=location_id,
            name="48 Rustaveli Avenue, Tbilisi",
            address="48 Rustaveli Avenue, Tbilisi",
            description="Test location",
            image_url="https://example.com/location.jpg",
            open_time=datetime.now(UTC).time(),
            close_time=datetime.now(UTC).time(),
        )

        slot_repo = DummySlotRepo([slot1, slot2])
        service = ReservationManagementService()
        service._reservation_repo = DummyReservationRepo(reservation)
        service._slot_repo = slot_repo
        service._table_repo = DummyTableRepo(table)
        service._location_repo = DummyLocationRepo(location)
        service._waiter_view_repo = DummyWaiterViewRepo()

        service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(slot1.status, SlotStatus.FREE)
        self.assertEqual(slot2.status, SlotStatus.FREE)

    def test_cancel_deletes_projection_row(self):
        """Cancelling a reservation removes it from the waiter-dashboard projection."""
        service, reservation, customer_id, _ = _build_service(start_in_minutes=120)

        service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(service._waiter_view_repo.deleted, [reservation.id])
        self.assertEqual(service._waiter_view_repo.upserted, [])

    def test_status_update_upserts_projection_row(self):
        """A non-cancel status change upserts the projection with the new status."""
        service, reservation, _, waiter_id = _build_service(start_in_minutes=120)

        service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        self.assertEqual(len(service._waiter_view_repo.upserted), 1)
        view = service._waiter_view_repo.upserted[0]
        self.assertEqual(view.id, reservation.id)
        self.assertEqual(view.status, ReservationStatus.IN_PROGRESS)
        self.assertEqual(view.table_number, 7)
        self.assertEqual(view.table_name, "7")
        self.assertEqual(service._waiter_view_repo.deleted, [])

    def test_list_for_waiter_table_returns_mapped_rows(self):
        """list_for_waiter_table resolves the waiter location and maps projection rows."""
        service, reservation, customer_id, waiter_id = _build_service(
            start_in_minutes=120
        )
        row = ReservationWaiterView(
            id=reservation.id,
            customer_id=customer_id,
            waiter_id=waiter_id,
            location_id=uuid4(),
            location_address="48 Rustaveli Avenue, Tbilisi",
            table_number=7,
            table_name="7",
            date="2026-05-16",
            time_from="12:00",
            time_to="13:30",
            guests_number=4,
            status=ReservationStatus.RESERVED,
        )
        service._waiter_view_repo = DummyWaiterViewRepo(rows=[row])

        response = service.list_for_waiter_table(
            waiter_id=waiter_id,
            date="2026-05-16",
            time_from="12:00",
            table_name="7",
        )

        self.assertEqual(len(response.reservations), 1)
        item = response.reservations[0]
        self.assertEqual(item.reservation_id, str(reservation.id))
        self.assertEqual(item.customer_id, str(customer_id))
        self.assertEqual(item.location_address, "48 Rustaveli Avenue, Tbilisi")
        self.assertEqual(item.table_number, 7)
        self.assertEqual(item.time_from, "12:00")
        self.assertEqual(item.time_to, "13:30")
        self.assertEqual(item.guests_number, 4)

    def test_list_for_waiter_table_passes_waiter_id_to_repo(self):
        """list_for_waiter_table forwards the caller's waiter_id to the projection query."""
        service, reservation, customer_id, waiter_id = _build_service(
            start_in_minutes=120
        )
        row = ReservationWaiterView(
            id=reservation.id,
            customer_id=customer_id,
            waiter_id=waiter_id,
            location_id=uuid4(),
            location_address="48 Rustaveli Avenue, Tbilisi",
            table_number=7,
            table_name="7",
            date="2026-05-16",
            time_from="12:00",
            time_to="13:30",
            guests_number=4,
            status=ReservationStatus.RESERVED,
        )
        dummy_repo = DummyWaiterViewRepo(rows=[row])
        service._waiter_view_repo = dummy_repo

        service.list_for_waiter_table(
            waiter_id=waiter_id,
            date="2026-05-16",
            time_from="12:00",
            table_name="7",
        )

        self.assertEqual(dummy_repo.last_waiter_id, waiter_id)

    def test_list_for_waiter_table_unknown_waiter_returns_403(self):
        """A caller without a waiter profile is forbidden from the table view."""
        service, _, _, _ = _build_service(start_in_minutes=120)
        service._waiter_repo = DummyWaiterRepo(None)

        with self.assertRaises(ApplicationException) as ctx:
            service.list_for_waiter_table(
                waiter_id=uuid4(),
                date="2026-05-16",
                time_from="12:00",
                table_name="7",
            )

        self.assertEqual(ctx.exception.code, 403)


class TestReservationManagementServiceSqsPublishing(unittest.TestCase):
    """Tests verifying SQS event publishing on reservation mutations."""

    def test_update_publishes_updated_event_for_in_progress(self):
        """update_reservation publishes UPDATED when status moves to IN_PROGRESS."""
        service, reservation, _, waiter_id = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs

        service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        mock_sqs.publish.assert_called_once()
        message = mock_sqs.publish.call_args.args[1]
        self.assertIsInstance(message, ReservationEventMessage)
        self.assertEqual(message.event_type, ReservationEventType.UPDATED)

    def test_update_publishes_completed_event_for_finished(self):
        """update_reservation publishes COMPLETED when status moves to FINISHED."""
        service, reservation, _, waiter_id = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs

        # Advance to IN_PROGRESS first (state machine requirement)
        reservation.status = ReservationStatus.IN_PROGRESS

        service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.FINISHED),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        message = mock_sqs.publish.call_args.args[1]
        self.assertEqual(message.event_type, ReservationEventType.COMPLETED)

    def test_cancel_publishes_cancelled_event(self):
        """cancel_reservation publishes CANCELLED event."""
        service, reservation, customer_id, _ = _build_service()
        mock_sqs = MagicMock()
        service._sqs = mock_sqs

        service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        mock_sqs.publish.assert_called_once()
        message = mock_sqs.publish.call_args.args[1]
        self.assertIsInstance(message, ReservationEventMessage)
        self.assertEqual(message.event_type, ReservationEventType.CANCELLED)

    def test_sqs_none_does_not_raise_on_update(self):
        """update_reservation completes normally when sqs_service is None."""
        service, reservation, _, waiter_id = _build_service()
        service._sqs = None

        view = service.update_reservation(
            reservation_id=reservation.id,
            request=UpdateReservationRequest(status=ReservationStatus.IN_PROGRESS),
            actor_id=waiter_id,
            role=UserRole.WAITER,
        )

        self.assertEqual(view.status, ReservationStatus.IN_PROGRESS)

    def test_sqs_none_does_not_raise_on_cancel(self):
        """cancel_reservation completes normally when sqs_service is None."""
        service, reservation, customer_id, _ = _build_service()
        service._sqs = None

        view = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(view.status, ReservationStatus.CANCELLED)

    def test_sqs_failure_does_not_affect_cancel_response(self):
        """cancel_reservation returns the correct view even if SqsService.publish raises."""
        service, reservation, customer_id, _ = _build_service()
        mock_sqs = MagicMock()
        mock_sqs.publish.side_effect = RuntimeError("SQS down")
        service._sqs = mock_sqs

        view = service.cancel_reservation(
            reservation_id=reservation.id,
            actor_id=customer_id,
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(view.status, ReservationStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()

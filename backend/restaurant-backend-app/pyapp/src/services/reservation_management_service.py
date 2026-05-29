"""Service layer for reservation dashboard, actions, and status lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from domain.reservation import Reservation
from dto.reservation_management import (
    AllowedActions,
    ReservationListResponse,
    ReservationView,
    UpdateReservationRequest,
)
from enums.http_status_code import HttpStatusCode
from enums.reservation_status import ReservationStatus
from enums.slot_status import SlotStatus
from enums.user_role import UserRole
from repositories.location_repository import LocationRepository
from repositories.reservation_repository import ReservationRepository
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository


class ReservationManagementService:
    """Encapsulates permission checks and reservation action business rules."""

    _CUTOFF_MINUTES = 30

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Create repository dependencies used by reservation lifecycle operations."""
        cfg = settings or AppConfig()
        self._reservation_repo = ReservationRepository(cfg)
        self._slot_repo = SlotRepository(cfg)
        self._table_repo = TableRepository(cfg)
        self._location_repo = LocationRepository(cfg)

    def list_for_dashboard(
        self,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationListResponse:
        """Return reservations visible to a customer or assigned waiter."""
        actor_uuid = self._coerce_uuid(actor_id)

        if role == UserRole.CUSTOMER:
            reservations = self._reservation_repo.find_by_customer_id(actor_uuid)
        elif role == UserRole.WAITER:
            reservations = self._reservation_repo.find_by_waiter_id(actor_uuid)
        else:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Role is not allowed to access reservations",
            )

        views = [
            self._build_reservation_view(
                reservation=reservation,
                actor_id=actor_uuid,
                role=role,
            )
            for reservation in reservations
        ]
        views.sort(key=lambda item: (item.date, item.time_from), reverse=True)
        return ReservationListResponse(reservations=views)

    def get_reservation(
        self,
        reservation_id: UUID | str,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationView:
        """Return a single reservation if actor has access."""
        reservation = self._get_accessible_reservation(
            reservation_id=reservation_id,
            actor_id=actor_id,
            role=role,
        )

        return self._build_reservation_view(
            reservation=reservation,
            actor_id=self._coerce_uuid(actor_id),
            role=role,
        )

    def update_reservation(
        self,
        reservation_id: UUID | str,
        request: UpdateReservationRequest,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationView:
        """Apply allowed edits/status updates and return refreshed reservation payload."""
        actor_uuid = self._coerce_uuid(actor_id)
        reservation = self._get_accessible_reservation(
            reservation_id=reservation_id,
            actor_id=actor_uuid,
            role=role,
        )
        slots = self._get_reservation_slots(reservation)

        start_time = min(slot.start_time for slot in slots)

        if request.guests_number is not None:
            self._ensure_editable(reservation, actor_uuid, role, start_time)
            table = self._table_repo.get(slots[0].table_id)
            if table and request.guests_number > table.capacity:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    [
                        {
                            "field": "guestsNumber",
                            "message": (
                                f"Guests number exceeds table capacity ({table.capacity})"
                            ),
                        }
                    ],
                )
            reservation.number_of_guests = request.guests_number

        if request.status is not None:
            self._apply_status_transition(
                reservation=reservation,
                new_status=request.status,
                actor_id=actor_uuid,
                role=role,
                start_time=start_time,
                slots=slots,
            )

        self._reservation_repo.update(reservation)
        return self._build_reservation_view(reservation, actor_uuid, role)

    def cancel_reservation(
        self,
        reservation_id: UUID | str,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationView:
        """Cancel a reservation if caller is customer or assigned waiter before cutoff."""
        actor_uuid = self._coerce_uuid(actor_id)
        reservation = self._get_accessible_reservation(
            reservation_id=reservation_id,
            actor_id=actor_uuid,
            role=role,
        )
        slots = self._get_reservation_slots(reservation)

        start_time = min(slot.start_time for slot in slots)
        self._ensure_editable(reservation, actor_uuid, role, start_time)

        reservation.status = ReservationStatus.CANCELLED
        self._release_slots(slots)

        self._reservation_repo.update(reservation)
        return self._build_reservation_view(reservation, actor_uuid, role)

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID:
        """Convert UUID-like values and reject malformed identity strings."""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (ValueError, TypeError) as exc:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNAUTHORIZED,
                "Invalid authenticated identity",
            ) from exc

    def _get_accessible_reservation(
        self,
        reservation_id: UUID | str,
        actor_id: UUID | str,
        role: str,
    ) -> Reservation:
        """Load reservation and ensure actor has ownership/assignment access."""
        reservation_uuid = self._coerce_uuid(reservation_id)
        actor_uuid = self._coerce_uuid(actor_id)

        reservation = self._reservation_repo.get(reservation_uuid)
        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation not found",
            )

        if (role, actor_uuid) in {
            (UserRole.CUSTOMER, reservation.customer_id),
            (UserRole.WAITER, reservation.waiter_id),
        }:
            return reservation

        raise ApplicationException(
            HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
            "You are not allowed to access this reservation",
        )

    def _build_reservation_view(
        self,
        reservation: Reservation,
        actor_id: UUID,
        role: str,
    ) -> ReservationView:
        """Build a frontend-friendly reservation payload with action flags."""
        slots = self._get_reservation_slots(reservation)

        start_time = min(slot.start_time for slot in slots)
        end_time = max(slot.end_time for slot in slots)
        table = self._table_repo.get(slots[0].table_id)
        location = self._location_repo.get(table.location_id) if table else None

        can_edit, can_cancel, cutoff_reason = self._compute_actions(
            reservation=reservation,
            actor_id=actor_id,
            role=role,
            start_time=start_time,
        )

        return ReservationView(
            reservation_id=str(reservation.id),
            status=reservation.status,
            customer_id=str(reservation.customer_id)
            if reservation.customer_id
            else None,
            waiter_id=str(reservation.waiter_id) if reservation.waiter_id else None,
            location_id=str(table.location_id) if table else None,
            location_address=location.address if location else None,
            table_number=table.table_number if table else None,
            date=start_time.date().isoformat(),
            time_from=start_time.strftime("%H:%M"),
            time_to=end_time.strftime("%H:%M"),
            guests_number=reservation.number_of_guests,
            allowed_actions=AllowedActions(
                can_edit=can_edit,
                can_cancel=can_cancel,
            ),
            cutoff_reason=cutoff_reason,
        )

    def _compute_actions(
        self,
        reservation: Reservation,
        actor_id: UUID,
        role: str,
        start_time,
    ) -> tuple[bool, bool, str | None]:
        """Return edit/cancel flags and cutoff reason when actions are disabled."""
        is_owner = role == UserRole.CUSTOMER and reservation.customer_id == actor_id
        is_assigned_waiter = (
            role == UserRole.WAITER and reservation.waiter_id == actor_id
        )
        is_action_actor = is_owner or is_assigned_waiter

        if not is_action_actor:
            return (
                False,
                False,
                "Only customer or assigned waiter can manage this reservation",
            )

        if reservation.status != ReservationStatus.RESERVED:
            return False, False, "Actions are available only for RESERVED reservations"

        if self._is_cutoff_reached(start_time):
            return (
                False,
                False,
                f"Edit/cancel are disabled {self._CUTOFF_MINUTES} minutes before start",
            )

        return True, True, None

    def _ensure_editable(
        self, reservation: Reservation, actor_id: UUID, role: str, start_time
    ) -> None:
        """Raise 422/403 when edit/cancel preconditions are not met."""
        can_edit, _, reason = self._compute_actions(
            reservation=reservation,
            actor_id=actor_id,
            role=role,
            start_time=start_time,
        )
        if not can_edit:
            code = (
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE
                if reason and reason.startswith("Only customer or assigned waiter")
                else HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY
            )
            raise ApplicationException(code, reason or "Reservation cannot be edited")

    def _apply_status_transition(
        self,
        reservation: Reservation,
        new_status: ReservationStatus,
        actor_id: UUID,
        role: str,
        start_time,
        slots,
    ) -> None:
        """Apply allowed status transitions for reservation lifecycle."""
        current = reservation.status

        if new_status == current:
            return

        if new_status == ReservationStatus.CANCELLED:
            self._ensure_editable(reservation, actor_id, role, start_time)
            reservation.status = ReservationStatus.CANCELLED
            self._release_slots(slots)
            return

        if role != UserRole.WAITER or reservation.waiter_id != actor_id:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only assigned waiter can change this reservation status",
            )

        if (
            current == ReservationStatus.RESERVED
            and new_status == ReservationStatus.IN_PROGRESS
        ):
            reservation.status = ReservationStatus.IN_PROGRESS
            return

        if (
            current == ReservationStatus.IN_PROGRESS
            and new_status == ReservationStatus.FINISHED
        ):
            reservation.status = ReservationStatus.FINISHED
            return

        raise ApplicationException(
            HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
            f"Invalid status transition from {current} to {new_status}",
        )

    def _is_cutoff_reached(self, start_time) -> bool:
        """Return True when reservation starts within the non-editable cutoff window."""
        now_utc = datetime.now(UTC)
        return now_utc + timedelta(minutes=self._CUTOFF_MINUTES) >= start_time

    def _get_reservation_slots(self, reservation: Reservation):
        slots = self._slot_repo.find_by_ids(reservation.slot_ids)
        if slots:
            return slots
        raise ApplicationException(
            HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
            "Reservation slots not found",
        )

    def _release_slots(self, slots) -> None:
        """Set all reservation slots back to FREE state."""
        for slot in slots:
            self._slot_repo.update_status(
                slot.id,
                SlotStatus.FREE,
                expected=SlotStatus.RESERVED,
            )

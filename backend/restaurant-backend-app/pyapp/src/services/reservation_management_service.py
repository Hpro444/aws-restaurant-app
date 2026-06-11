"""Service layer for reservation dashboard, actions, and status lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from commons.uuid_utils import parse_uuid_or_raise
from domain.reservation import Reservation
from domain.reservation_waiter_view import ReservationWaiterView
from dto.reservation_event import ReservationEventMessage, ReservationEventType
from dto.reservation_management import (
    AllowedActions,
    ReservationListResponse,
    ReservationView,
    UpdateReservationRequest,
)
from dto.waiter_reservations import (
    ReservationWaiterViewDTO,
    WaiterReservationListResponse,
)
from enums import HttpStatusCode, ReservationStatus, SlotStatus, UserRole
from repositories.customer_repository import CustomerRepository
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.feedback_service_repository import FeedbackServiceRepository
from repositories.location_repository import LocationRepository
from repositories.reservation_repository import ReservationRepository
from repositories.reservation_waiter_view_repository import (
    ReservationWaiterViewRepository,
)
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository
from repositories.waiter_repository import WaiterRepository

from services.sqs_service import SqsService


class ReservationManagementService:
    """Encapsulates permission checks and reservation action business rules."""

    _CUTOFF_MINUTES = 30

    def __init__(
        self,
        settings: AppConfig | None = None,
        reservation_repository: ReservationRepository | None = None,
        slot_repository: SlotRepository | None = None,
        table_repository: TableRepository | None = None,
        location_repository: LocationRepository | None = None,
        waiter_repository: WaiterRepository | None = None,
        waiter_view_repository: ReservationWaiterViewRepository | None = None,
        customer_repository: CustomerRepository | None = None,
        feedback_service_repository: FeedbackServiceRepository | None = None,
        feedback_cuisine_repository: FeedbackCuisineRepository | None = None,
        sqs_service: SqsService | None = None,
    ) -> None:
        """Create repository dependencies, creating defaults when omitted.

        Args:
            settings: Shared application config.
            reservation_repository: Optional ReservationRepository instance.
            slot_repository: Optional SlotRepository instance.
            table_repository: Optional TableRepository instance.
            location_repository: Optional LocationRepository instance.
            waiter_repository: Optional WaiterRepository instance.
            waiter_view_repository: Optional ReservationWaiterViewRepository instance.
            customer_repository: Optional CustomerRepository instance.
            feedback_service_repository: Optional FeedbackServiceRepository instance.
            feedback_cuisine_repository: Optional FeedbackCuisineRepository instance.
            sqs_service: Optional SqsService for publishing reservation events.

        """
        cfg = settings or AppConfig()
        self._settings = cfg
        self._reservation_repo = reservation_repository or ReservationRepository(cfg)
        self._slot_repo = slot_repository or SlotRepository(cfg)
        self._table_repo = table_repository or TableRepository(cfg)
        self._location_repo = location_repository or LocationRepository(cfg)
        self._waiter_repo = waiter_repository or WaiterRepository(cfg)
        self._waiter_view_repo = (
            waiter_view_repository or ReservationWaiterViewRepository(cfg)
        )
        self._customer_repo = customer_repository or CustomerRepository(cfg)
        self._feedback_service_repo = (
            feedback_service_repository or FeedbackServiceRepository(cfg)
        )
        self._feedback_cuisine_repo = (
            feedback_cuisine_repository or FeedbackCuisineRepository(cfg)
        )
        self._sqs = sqs_service

    def list_for_dashboard(
        self,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationListResponse:
        """Return reservations visible to a customer or assigned waiter."""
        actor_uuid = parse_uuid_or_raise(actor_id)

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

    def list_for_waiter_table(
        self,
        waiter_id: UUID | str,
        date: str,
        time_from: str,
        table_name: str,
    ) -> WaiterReservationListResponse:
        """Return reservations for one date/start-time/table at the waiter's location.

        The caller's ``location_id`` is resolved from their Waiter profile, then a
        single GSI query returns the matching denormalized projection rows.
        """
        waiter_uuid = parse_uuid_or_raise(waiter_id)
        waiter = self._waiter_repo.get(waiter_uuid)
        if waiter is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Waiter profile not found",
            )

        rows = self._waiter_view_repo.query_for_table(
            location_id=waiter.location_id,
            date=date,
            time_from=time_from,
            table_name=table_name,
            waiter_id=waiter_uuid,
        )

        views = [
            ReservationWaiterViewDTO(
                reservation_id=str(row.id),
                customer_id=str(row.customer_id) if row.customer_id else None,
                created_by=row.created_by,
                location_address=row.location_address,
                table_number=row.table_number,
                date=row.date,
                time_from=row.time_from,
                time_to=row.time_to,
                guests_number=row.guests_number,
                status=row.status.value
                if hasattr(row.status, "value")
                else str(row.status),
            )
            for row in rows
        ]
        views.sort(key=lambda item: item.time_from)
        return WaiterReservationListResponse(reservations=views)

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
            actor_id=parse_uuid_or_raise(actor_id),
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
        actor_uuid = parse_uuid_or_raise(actor_id)
        reservation = self._get_accessible_reservation(
            reservation_id=reservation_id,
            actor_id=actor_uuid,
            role=role,
        )
        slots = self._get_reservation_slots(reservation)

        start_time = min(slot.start_time for slot in slots)

        if request.guests_number is not None:
            self._ensure_editable(reservation, actor_uuid, role, start_time)
            self._ensure_guest_count_fits_table(request.guests_number, slots)
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
        view = self._build_reservation_view(reservation, actor_uuid, role)
        self._sync_projection(reservation, view)
        if self._sqs is not None:
            try:
                event_type = (
                    ReservationEventType.FINISHED
                    if view.status == ReservationStatus.FINISHED
                    else ReservationEventType.UPDATED
                )
                self._sqs.publish(
                    self._settings.event_queue_url,
                    self._build_event_message(event_type, view),
                )
            except Exception:
                logger.error("SQS publish failed in update_reservation", exc_info=True)
        return view

    def cancel_reservation(
        self,
        reservation_id: UUID | str,
        actor_id: UUID | str,
        role: str,
    ) -> ReservationView:
        """Cancel a reservation if caller is customer or assigned waiter before cutoff."""
        actor_uuid = parse_uuid_or_raise(actor_id)
        reservation = self._get_accessible_reservation(
            reservation_id=reservation_id,
            actor_id=actor_uuid,
            role=role,
        )

        slots = self._slot_repo.find_by_ids(reservation.slot_ids)
        if not slots:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation slots not found",
            )

        start_time = min(slot.start_time for slot in slots)
        self._ensure_editable(reservation, actor_uuid, role, start_time)

        reservation.status = ReservationStatus.CANCELLED
        self._release_slots(slots)

        self._reservation_repo.update(reservation)
        view = self._build_reservation_view(reservation, actor_uuid, role)
        self._sync_projection(reservation, view)
        if self._sqs is not None:
            try:
                self._sqs.publish(
                    self._settings.event_queue_url,
                    self._build_event_message(ReservationEventType.CANCELLED, view),
                )
            except Exception:
                logger.error("SQS publish failed in cancel_reservation", exc_info=True)
        return view

    def _get_accessible_reservation(
        self,
        reservation_id: UUID | str,
        actor_id: UUID | str,
        role: str,
    ) -> Reservation:
        """Load reservation and ensure actor has ownership/assignment access."""
        reservation_uuid = parse_uuid_or_raise(reservation_id)
        actor_uuid = parse_uuid_or_raise(actor_id)

        reservation = self._reservation_repo.get(reservation_uuid)
        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation not found",
            )

        if (role, actor_uuid) in {
            (UserRole.CUSTOMER.value, reservation.customer_id),
            (UserRole.WAITER.value, reservation.waiter_id),
        }:
            return reservation

        raise ApplicationException(
            HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
            "You are not allowed to access this reservation",
        )

    def _get_reservation_slots(self, reservation: Reservation):
        """Return reservation slots or raise 404 when referenced slots are missing."""
        slots = self._slot_repo.find_by_ids(reservation.slot_ids)
        if not slots:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation slots not found",
            )
        return slots

    def _build_reservation_view(
        self,
        reservation: Reservation,
        actor_id: UUID,
        role: str,
    ) -> ReservationView:
        """Build a frontend-friendly reservation payload with action flags."""
        slots = self._slot_repo.find_by_ids(reservation.slot_ids)
        if not slots:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation slots not found",
            )

        start_time = min(slot.start_time for slot in slots)
        end_time = max(slot.end_time for slot in slots)
        table = self._table_repo.get(slots[0].table_id)
        location = self._location_repo.get(table.location_id) if table else None
        feedback_exists = self._has_feedback_for_reservation(reservation.id)

        can_edit, can_cancel, can_leave_feedback, can_edit_feedback, cutoff_reason = (
            self._compute_actions(
                reservation=reservation,
                actor_id=actor_id,
                role=role,
                start_time=start_time,
                feedback_exists=feedback_exists,
            )
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
                can_leave_feedback=can_leave_feedback,
                can_edit_feedback=can_edit_feedback,
            ),
            cutoff_reason=cutoff_reason,
        )

    def _build_event_message(
        self,
        event_type: ReservationEventType,
        view: ReservationView,
    ) -> ReservationEventMessage:
        """Build a flat ReservationEventMessage from a reservation view."""
        return ReservationEventMessage(
            event_type=event_type,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            reservation_id=view.reservation_id,
            status=view.status,
            customer_id=view.customer_id,
            waiter_id=view.waiter_id,
            location_id=view.location_id,
            location_address=view.location_address,
            table_number=view.table_number,
            date=view.date,
            time_from=view.time_from,
            time_to=view.time_to,
            guests_number=view.guests_number,
            allowed_actions=view.allowed_actions,
            cutoff_reason=view.cutoff_reason,
        )

    def _sync_projection(self, reservation: Reservation, view: ReservationView) -> None:
        """Keep the waiter-dashboard read model in step with a reservation change.

        Cancelled reservations are removed from the projection; otherwise the
        flattened row is upserted. The upsert is skipped when the table or
        location could not be resolved (nothing to key the row on).
        """
        if reservation.status == ReservationStatus.CANCELLED:
            self._waiter_view_repo.delete(reservation.id)
            return
        if view.location_id is None or view.table_number is None:
            return
        self._waiter_view_repo.update(self._to_projection(reservation, view))

    def _resolve_created_by(self, reservation: Reservation) -> str | None:
        """Return the display label: 'Customer <name>' for customer bookings, 'Waiter <name> (Visitor)' for visitor bookings."""
        if reservation.customer_id is not None:
            try:
                customer = self._customer_repo.get(reservation.customer_id)
            except Exception:
                logger.warning(
                    "Failed to resolve customer profile for reservation projection",
                    reservation_id=str(reservation.id),
                    customer_id=str(reservation.customer_id),
                    exc_info=True,
                )
                customer = None
            if customer:
                return f"Customer {customer.fname} {customer.lname}".strip()
        if reservation.waiter_id is not None:
            waiter = self._waiter_repo.get(reservation.waiter_id)
            if waiter:
                return f"Waiter {waiter.fname} {waiter.lname} (Visitor)"
        return None

    def _has_feedback_for_reservation(self, reservation_id: UUID) -> bool:
        """Return True when either service or cuisine feedback exists for reservation."""
        service_feedback_id = uuid5(NAMESPACE_URL, f"service:{reservation_id}")
        cuisine_feedback_id = uuid5(NAMESPACE_URL, f"culinary:{reservation_id}")

        try:
            return bool(
                self._feedback_service_repo.get(service_feedback_id)
                or self._feedback_cuisine_repo.get(cuisine_feedback_id)
            )
        except Exception:
            logger.warning(
                "Failed to check feedback existence for reservation",
                reservation_id=str(reservation_id),
                exc_info=True,
            )
            return False

    def _to_projection(
        self, reservation: Reservation, view: ReservationView
    ) -> ReservationWaiterView:
        """Map an enriched ReservationView to its waiter-dashboard projection row."""
        return ReservationWaiterView(
            id=reservation.id,
            customer_id=reservation.customer_id,
            created_by=self._resolve_created_by(reservation),
            waiter_id=reservation.waiter_id,
            location_id=view.location_id,
            location_address=view.location_address,
            table_number=view.table_number,
            table_name=str(view.table_number),
            date=view.date,
            time_from=view.time_from,
            time_to=view.time_to,
            guests_number=reservation.number_of_guests,
            status=reservation.status,
        )

    def _compute_actions(
        self,
        reservation: Reservation,
        actor_id: UUID,
        role: str,
        start_time,
        feedback_exists: bool,
    ) -> tuple[bool, bool, bool, bool, str | None]:
        """Return action flags and cutoff reason for reservation controls."""
        is_owner = role == UserRole.CUSTOMER and reservation.customer_id == actor_id
        is_assigned_waiter = (
            role == UserRole.WAITER and reservation.waiter_id == actor_id
        )
        is_action_actor = is_owner or is_assigned_waiter
        feedback_status_eligible = reservation.status in {
            ReservationStatus.IN_PROGRESS,
            ReservationStatus.FINISHED,
        }
        can_leave_feedback = (
            is_owner and feedback_status_eligible and not feedback_exists
        )
        can_edit_feedback = is_owner and feedback_status_eligible and feedback_exists

        if not is_action_actor:
            return (
                False,
                False,
                False,
                False,
                "Only customer or assigned waiter can manage this reservation",
            )

        if reservation.status != ReservationStatus.RESERVED:
            return (
                False,
                False,
                can_leave_feedback,
                can_edit_feedback,
                "Actions are available only for RESERVED reservations",
            )

        if role == UserRole.CUSTOMER and self._is_cutoff_reached(start_time):
            return (
                False,
                False,
                can_leave_feedback,
                can_edit_feedback,
                f"Edit/cancel are disabled {self._CUTOFF_MINUTES} minutes before start",
            )

        return True, True, can_leave_feedback, can_edit_feedback, None

    def _ensure_editable(
        self, reservation: Reservation, actor_id: UUID, role: str, start_time
    ) -> None:
        """Raise 422/403 when edit/cancel preconditions are not met."""
        can_edit, _, _, _, reason = self._compute_actions(
            reservation=reservation,
            actor_id=actor_id,
            role=role,
            start_time=start_time,
            feedback_exists=False,
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

        if role != UserRole.WAITER or reservation.waiter_id != actor_id:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only assigned waiter can change this reservation status",
            )

        if new_status == ReservationStatus.CANCELLED:
            self._ensure_editable(reservation, actor_id, role, start_time)
            reservation.status = ReservationStatus.CANCELLED
            self._release_slots(slots)
            return

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

    def _release_slots(self, slots) -> None:
        """Set all reservation slots back to FREE state."""
        for slot in slots:
            self._slot_repo.update_status(
                slot.id,
                SlotStatus.FREE,
                expected=SlotStatus.RESERVED,
            )

    def _ensure_guest_count_fits_table(self, guests_number: int, slots) -> None:
        """Raise 422 when requested guest count exceeds reservation table capacity."""
        table = self._table_repo.get(slots[0].table_id)
        if table is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Table not found for reservation",
            )

        table_capacity = table.capacity
        exceeds_capacity = guests_number > table_capacity

        if not exceeds_capacity:
            return

        raise ApplicationException(
            HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
            [
                {
                    "field": "guestsNumber",
                    "message": f"Guests number exceeds table capacity ({table_capacity})",
                }
            ],
        )

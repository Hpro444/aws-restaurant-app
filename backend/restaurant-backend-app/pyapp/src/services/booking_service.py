"""Service that creates a customer reservation from a selected timeslot."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from commons.uuid_utils import coerce_uuid
from domain.reservation import Reservation
from domain.reservation_waiter_view import ReservationWaiterView
from domain.slot import Slot
from domain.table import Table
from dto.create_booking import CreateBookingRequest, CreateBookingResponse
from dto.reservation_event import ReservationEventMessage, ReservationEventType
from dto.reservation_management import AllowedActions, ReservationView
from enums.http_status_code import HttpStatusCode
from enums.reservation_status import ReservationStatus
from enums.slot_status import SlotStatus
from repositories.customer_repository import CustomerRepository
from repositories.location_repository import LocationRepository
from repositories.reservation_repository import ReservationRepository
from repositories.reservation_waiter_view_repository import (
    ReservationWaiterViewRepository,
)
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository
from repositories.waiter_repository import WaiterRepository

from services.sqs_service import SqsService


class BookingService:
    """Persist a reservation for the slot chain identified by a booking request.

    The flow:
        1. Resolve the table by ``locationId`` + ``tableNumber``.
        2. Enforce that ``guestsNumber`` fits the table capacity.
        3. Load all slots for the table on the requested date.
          4. Identify the slot whose ``start_time`` matches ``timeFrom`` and
              the slot whose ``end_time`` matches ``timeTo``; build the chain
              of every slot between them (inclusive).
          5. Enforce slot-chain duration business rules:
              each slot lasts 90 minutes, each inter-slot pause is 15 minutes,
              and total elapsed time equals ``90*n + 15*(n-1)`` minutes.
          6. Verify each chained slot has ``status == FREE``.
          7. Atomically claim each slot via a DynamoDB conditional update;
           on the first contention failure, revert previously-claimed
           slots and surface a 409.
          8. Persist the :class:`Reservation` row with ``status=RESERVED``.
    """

    _INVALID_RANGE_MESSAGE = "Invalid time range for the selected slots"
    _SLOT_CONFLICT_MESSAGE = "One or more selected slots are already reserved"

    def __init__(
        self,
        settings: AppConfig | None = None,
        table_repository: TableRepository | None = None,
        slot_repository: SlotRepository | None = None,
        reservation_repository: ReservationRepository | None = None,
        location_repository: LocationRepository | None = None,
        waiter_repository: WaiterRepository | None = None,
        waiter_view_repository: ReservationWaiterViewRepository | None = None,
        sqs_service: SqsService | None = None,
    ) -> None:
        """Create the repositories used by this service, creating defaults when omitted.

        Args:
            settings: Shared application config.
            table_repository: Optional TableRepository instance.
            slot_repository: Optional SlotRepository instance.
            reservation_repository: Optional ReservationRepository instance.
            location_repository: Optional LocationRepository instance.
            waiter_repository: Optional WaiterRepository instance.
            waiter_view_repository: Optional ReservationWaiterViewRepository instance.
            sqs_service: Optional SqsService for publishing reservation events.

        """
        cfg = settings or AppConfig()
        self._settings = cfg
        self._table_repo = table_repository or TableRepository(cfg)
        self._slot_repo = slot_repository or SlotRepository(cfg)
        self._reservation_repo = reservation_repository or ReservationRepository(cfg)
        self._location_repo = location_repository or LocationRepository(cfg)
        self._customer_repo = CustomerRepository(cfg)
        self._waiter_repo = waiter_repository or WaiterRepository(cfg)
        self._waiter_view_repo = (
            waiter_view_repository or ReservationWaiterViewRepository(cfg)
        )
        self._sqs = sqs_service

    def create_booking(
        self,
        request: CreateBookingRequest,
        customer_id: UUID | str | None,
        client_name: str | None = None,
        waiter_id: UUID | str | None = None,
    ) -> CreateBookingResponse:
        """Create a reservation for ``customer_id`` from ``request``.

        Args:
            request: Validated booking request DTO.
            customer_id: UUID (or its string form) of the booking customer,
                or ``None`` when a waiter creates a visitor reservation.
            client_name: Optional name for customer or visitor.
            waiter_id: Optional UUID of waiter creating the reservation.
                This value identifies the actor only; assignment is resolved from
                the preassigned waiter on ``slot[0]``.

        Returns:
            :class:`CreateBookingResponse` for the persisted reservation.

        Raises:
            ApplicationException: With the appropriate HTTP status code
                for validation, lookup, capacity, or contention failures.

        """
        customer_uuid = (
            coerce_uuid(customer_id, field_name="customer_id")
            if customer_id is not None
            else None
        )
        resolved_client_name = self._resolve_client_name(customer_uuid, client_name)

        table = self._find_table(request.location_id, request.table_number)
        self._check_capacity(table, request.guests_number)

        location = self._location_repo.get(request.location_id)
        if not location:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Location not found",
            )

        slots_for_day = self._slot_repo.find_by_table_id_and_date(
            table.id, request.date
        )
        if not slots_for_day:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "No slots exist for the selected table on this date",
            )

        chain = self._resolve_slot_chain(
            slots_for_day,
            request.time_from,
            request.time_to,
        )
        self._check_within_operating_hours(chain, location)
        self._ensure_start_time_in_future(chain)
        self._ensure_all_free(chain)
        self._claim_slots(chain)

        assigned_waiter_id = self._resolve_waiter_for_chain(chain, table.location_id)

        reservation = Reservation(
            id=uuid4(),
            customer_id=customer_uuid,
            client_name=resolved_client_name,
            waiter_id=assigned_waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[s.id for s in chain],
            status=ReservationStatus.RESERVED,
            number_of_guests=request.guests_number,
        )
        try:
            self._reservation_repo.create(reservation)
        except ApplicationException:
            self._release_slots(chain)
            raise

        # Project the reservation into the waiter-dashboard read model. This is a
        # best-effort upsert (the repository swallows DynamoDB errors) so a
        # projection hiccup never rolls back an already-committed reservation.
        self._waiter_view_repo.update(
            ReservationWaiterView(
                id=reservation.id,
                customer_id=customer_uuid,
                waiter_id=assigned_waiter_id,
                location_id=table.location_id,
                location_address=location.address,
                table_number=table.table_number,
                table_name=str(table.table_number),
                date=chain[0].start_time.date().isoformat(),
                time_from=chain[0].start_time.strftime("%H:%M"),
                time_to=chain[-1].end_time.strftime("%H:%M"),
                guests_number=reservation.number_of_guests,
                status=reservation.status,
            )
        )

        logger.info(
            "Reservation created",
            reservation_id=str(reservation.id),
            customer_id=str(customer_uuid) if customer_uuid else None,
            client_name=resolved_client_name,
            waiter_id=str(assigned_waiter_id) if assigned_waiter_id else None,
            slot_count=len(chain),
        )

        if self._sqs is not None:
            try:
                event_view = ReservationView(
                    reservation_id=str(reservation.id),
                    status=reservation.status,
                    customer_id=str(customer_uuid) if customer_uuid else None,
                    waiter_id=str(assigned_waiter_id) if assigned_waiter_id else None,
                    location_id=str(request.location_id),
                    location_address=location.address,
                    table_number=request.table_number,
                    date=request.date,
                    time_from=chain[0].start_time.strftime("%H:%M"),
                    time_to=chain[-1].end_time.strftime("%H:%M"),
                    guests_number=request.guests_number,
                    allowed_actions=AllowedActions(can_edit=True, can_cancel=True),
                    cutoff_reason=None,
                )
                self._sqs.publish(
                    self._settings.reservation_events_queue_url,
                    ReservationEventMessage(
                        event_type=ReservationEventType.CREATED,
                        reservation=event_view,
                        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    ),
                )
            except Exception:
                logger.error("SQS publish failed in create_booking", exc_info=True)

        return CreateBookingResponse(
            reservation_id=str(reservation.id),
            status=reservation.status,
            location_id=str(request.location_id),
            location_address=location.address,
            table_number=request.table_number,
            date=request.date,
            time_from=self._format_utc(chain[0].start_time),
            time_to=self._format_utc(chain[-1].end_time),
            guests_number=request.guests_number,
            client_name=resolved_client_name,
        )

    # ── Private helpers ─────────────────────────────────────────────

    def _resolve_waiter_for_chain(
        self,
        chain: list[Slot],
        location_id: UUID,
    ) -> UUID | None:
        """Resolve reservation waiter from ``slot[0]`` (fallback deterministic waiter).

        Seeded slots should always include ``waiter_id``; fallback exists only
        for backward compatibility with older data.
        """
        first_slot_waiter = chain[0].waiter_id
        if first_slot_waiter is not None:
            return first_slot_waiter

        waiters = self._waiter_repo.find_by_location_id(location_id)
        if not waiters:
            return None

        logger.warning(
            "Slot waiter_id missing; falling back to deterministic waiter",
            location_id=str(location_id),
            slot_id=str(chain[0].id),
        )
        return sorted(waiters, key=lambda waiter: str(waiter.id))[0].id

    def _resolve_client_name(
        self,
        customer_id: UUID | None,
        client_name: str | None,
    ) -> str | None:
        """Return reservation client name from explicit input or customer profile."""
        if client_name:
            return client_name.strip()

        if customer_id is None:
            return None

        customer = self._customer_repo.get(customer_id)
        if customer is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Customer not found",
            )

        full_name = f"{customer.fname} {customer.lname}".strip()
        return full_name or None

    def _find_table(self, location_id: UUID, table_number: int) -> Table:
        """Return the Table at ``location_id`` with matching ``table_number``.

        Raises:
            ApplicationException(404): No such table at the location.

        """
        tables = self._table_repo.find_by_location_id(location_id)
        for table in tables:
            if table.table_number == table_number:
                return table
        raise ApplicationException(
            HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
            "Table not found for the specified location",
        )

    @staticmethod
    def _check_capacity(table: Table, guests_number: int) -> None:
        """Reject the request with 422 when guests exceed capacity."""
        if guests_number > table.capacity:
            BookingService._raise_field_validation(
                "guestsNumber",
                f"Guests number exceeds table capacity ({table.capacity})",
            )

    def _resolve_slot_chain(
        self,
        slots_for_day: list[Slot],
        time_from: str,
        time_to: str,
    ) -> list[Slot]:
        """Find the inclusive ordered chain of slots between ``time_from`` and ``time_to``.

        Raises:
            ApplicationException(422): ``time_from`` does not match any
                slot's ``start_time`` or ``time_to`` does not match any
                slot's ``end_time``.

        """
        start_slot: Slot | None = None
        end_slot: Slot | None = None
        parsed_time_from = self._parse_utc_datetime(time_from)
        parsed_time_to = self._parse_utc_datetime(time_to)

        for slot in slots_for_day:
            if slot.start_time == parsed_time_from:
                start_slot = slot
            if slot.end_time == parsed_time_to:
                end_slot = slot

        if start_slot is None:
            self._raise_field_validation(
                "timeFrom",
                "timeFrom must match the start of an existing slot",
            )
        if end_slot is None:
            self._raise_field_validation(
                "timeTo",
                "timeTo must match the end of an existing slot",
            )

        ordered = sorted(slots_for_day, key=lambda s: s.start_time)
        chain = [
            s
            for s in ordered
            if s.start_time >= start_slot.start_time and s.end_time <= end_slot.end_time
        ]
        # The endpoints must be in the chain — if they are not (e.g.
        # mismatched ordering), surface a 422.
        if start_slot not in chain or end_slot not in chain:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Invalid time range for the selected slots",
            )

        self._validate_slot_chain_duration(chain)
        return chain

    def _validate_slot_chain_duration(self, chain: list[Slot]) -> None:
        """Validate reservation duration formula for the selected slot chain.

        The business rule is:
            total_duration = 90*n + 15*(n-1) minutes, n >= 1

        where ``n`` is the number of booked slots.

        Raises:
            ApplicationException(422): Chain violates slot duration,
                inter-slot break, or total elapsed duration constraints.

        """
        if not chain:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Invalid time range for the selected slots",
            )

        slot_length = timedelta(minutes=90)
        pause_length = timedelta(minutes=15)

        for slot in chain:
            if slot.end_time - slot.start_time != slot_length:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    "Invalid time range for the selected slots",
                )

        for previous, current in zip(chain, chain[1:]):
            if current.start_time - previous.end_time != pause_length:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    "Invalid time range for the selected slots",
                )

        n_slots = len(chain)
        expected_total = slot_length * n_slots + pause_length * (n_slots - 1)
        actual_total = chain[-1].end_time - chain[0].start_time
        if actual_total != expected_total:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Invalid time range for the selected slots",
            )

    @staticmethod
    def _check_within_operating_hours(chain: list[Slot], location) -> None:
        """Raise 422 if the last slot's end_time exceeds location's close_time.

        This ensures that a reservation chain (whether 90, 195, 300 minutes, etc.)
        never extends past the location's operating hours.
        """
        last_slot = chain[-1]
        last_slot_end_time = last_slot.end_time.time()

        if last_slot_end_time > location.close_time:
            BookingService._raise_field_validation(
                "timeTo",
                f"Reservation extends beyond location closing time ({location.close_time.strftime('%H:%M')})",
            )

    @staticmethod
    def _ensure_start_time_in_future(
        chain: list[Slot],
    ) -> None:
        """Raise 422 when the reservation starts in the past or at the current time."""
        first_slot_start = chain[0].start_time
        now_utc = datetime.now(UTC)
        if first_slot_start <= now_utc:
            BookingService._raise_field_validation(
                "timeFrom",
                "Cannot book a slot that starts in the past",
            )

    @staticmethod
    def _format_utc(dt: datetime) -> str:
        """Format datetime as UTC ISO string for API response."""
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_utc_datetime(raw_value: str) -> datetime:
        """Parse UTC datetime string for slot matching."""
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).astimezone(UTC)

    @staticmethod
    def _ensure_start_time_in_future(chain: list[Slot]) -> None:
        """Raise 422 when the reservation starts in the past or at the current time."""
        first_slot_start = chain[0].start_time
        now_utc = datetime.now(UTC)
        if first_slot_start <= now_utc:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [
                    {
                        "field": "timeFrom",
                        "message": "Cannot book a slot that starts in the past",
                    }
                ],
            )

    @staticmethod
    def _ensure_all_free(chain: list[Slot]) -> None:
        """Raise 409 if any slot in the chain is not currently FREE."""
        booked = [s for s in chain if s.status != SlotStatus.FREE]
        if booked:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_CONFLICT_CODE,
                BookingService._SLOT_CONFLICT_MESSAGE,
            )

    def _claim_slots(self, chain: list[Slot]) -> None:
        """Conditionally flip every slot in the chain to RESERVED.

        On the first contention failure, the slots already flipped are
        rolled back to FREE and a 409 is raised.

        """
        claimed: list[Slot] = []
        for slot in chain:
            ok = self._slot_repo.update_status(
                slot.id, SlotStatus.RESERVED, expected=SlotStatus.FREE
            )
            if not ok:
                self._release_slots(claimed)
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_CONFLICT_CODE,
                    self._SLOT_CONFLICT_MESSAGE,
                )
            slot.status = SlotStatus.RESERVED
            claimed.append(slot)

    @staticmethod
    def _raise_field_validation(field: str, message: str) -> None:
        """Raise a standardized 422 field validation error payload."""
        raise ApplicationException(
            HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
            [{"field": field, "message": message}],
        )

    def _release_slots(self, claimed: list[Slot]) -> None:
        """Best-effort revert of slots previously flipped to RESERVED."""
        for slot in claimed:
            self._slot_repo.update_status(
                slot.id, SlotStatus.FREE, expected=SlotStatus.RESERVED
            )
            slot.status = SlotStatus.FREE

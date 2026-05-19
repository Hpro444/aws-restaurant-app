"""Service that creates a customer reservation from a selected timeslot."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from domain.reservation import Reservation
from domain.slot import Slot
from domain.table import Table
from dto.create_booking import CreateBookingRequest, CreateBookingResponse
from enums.http_status_code import HttpStatusCode
from enums.reservation_status import ReservationStatus
from enums.slot_status import SlotStatus
from repositories.reservation_repository import ReservationRepository
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository


class BookingService:
    """Persist a reservation for the slot chain identified by a booking request.

    The flow:
        1. Resolve the table by ``locationId`` + ``tableNumber``.
        2. Enforce that ``guestsNumber`` fits the table capacity.
        3. Load all slots for the table on the requested date.
        4. Identify the slot whose ``start_time`` matches ``timeFrom`` and
           the slot whose ``end_time`` matches ``timeTo``; build the chain
           of every slot between them (inclusive).
        5. Verify each chained slot has ``status == FREE``.
        6. Atomically claim each slot via a DynamoDB conditional update;
           on the first contention failure, revert previously-claimed
           slots and surface a 409.
        7. Persist the :class:`Reservation` row with ``status=RESERVED``.
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Create the repositories used by this service.

        Args:
            settings: Shared application config.

        """
        cfg = settings or AppConfig()
        self._table_repo = TableRepository(cfg)
        self._slot_repo = SlotRepository(cfg)
        self._reservation_repo = ReservationRepository(cfg)

    def create_booking(
        self,
        request: CreateBookingRequest,
        customer_id: UUID | str,
    ) -> CreateBookingResponse:
        """Create a reservation for ``customer_id`` from ``request``.

        Args:
            request: Validated booking request DTO.
            customer_id: UUID (or its string form) of the booking customer.

        Returns:
            :class:`CreateBookingResponse` for the persisted reservation.

        Raises:
            ApplicationException: With the appropriate HTTP status code
                for validation, lookup, capacity, or contention failures.

        """
        customer_uuid = self._coerce_uuid(customer_id, field_name="customer_id")

        table = self._find_table(request.location_id, request.table_number)
        self._check_capacity(table, request.guests_number)

        slots_for_day = self._slot_repo.find_by_table_id_and_date(
            table.id, request.date
        )
        if not slots_for_day:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "No slots exist for the selected table on this date",
            )

        chain = self._resolve_slot_chain(
            slots_for_day, request.time_from, request.time_to
        )
        self._ensure_all_free(chain)
        self._claim_slots(chain)

        reservation = Reservation(
            id=uuid4(),
            customer_id=customer_uuid,
            waiter_id=None,
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

        logger.info(
            "Reservation created",
            reservation_id=str(reservation.id),
            customer_id=str(customer_uuid),
            slot_count=len(chain),
        )

        return CreateBookingResponse(
            reservation_id=str(reservation.id),
            status=reservation.status.value,
            location_id=str(request.location_id),
            table_number=request.table_number,
            date=request.date,
            time_from=chain[0].start_time.strftime("%H:%M"),
            time_to=chain[-1].end_time.strftime("%H:%M"),
            guests_number=request.guests_number,
        )

    # ── Private helpers ─────────────────────────────────────────────

    @staticmethod
    def _coerce_uuid(value: UUID | str, field_name: str) -> UUID:
        """Coerce ``value`` to UUID or raise a 401 if it cannot be parsed."""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except (ValueError, TypeError) as exc:
            logger.warning("Invalid UUID for field", field=field_name, value=value)
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNAUTHORIZED,
                "Invalid authenticated identity",
            ) from exc

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

    @staticmethod
    def _resolve_slot_chain(
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
        for slot in slots_for_day:
            if slot.start_time.strftime("%H:%M") == time_from:
                start_slot = slot
            if slot.end_time.strftime("%H:%M") == time_to:
                end_slot = slot

        if start_slot is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [
                    {
                        "field": "timeFrom",
                        "message": "timeFrom must match the start of an existing slot",
                    }
                ],
            )
        if end_slot is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [
                    {
                        "field": "timeTo",
                        "message": "timeTo must match the end of an existing slot",
                    }
                ],
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
        return chain

    @staticmethod
    def _ensure_all_free(chain: list[Slot]) -> None:
        """Raise 409 if any slot in the chain is not currently FREE."""
        booked = [s for s in chain if s.status != SlotStatus.FREE]
        if booked:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_CONFLICT_CODE,
                "One or more selected slots are already reserved",
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
                    "One or more selected slots are already reserved",
                )
            slot.status = SlotStatus.RESERVED
            claimed.append(slot)

    def _release_slots(self, claimed: list[Slot]) -> None:
        """Best-effort revert of slots previously flipped to RESERVED."""
        for slot in claimed:
            self._slot_repo.update_status(
                slot.id, SlotStatus.FREE, expected=SlotStatus.RESERVED
            )
            slot.status = SlotStatus.FREE

"""Service that computes table availability for a given location and date."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Optional
from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.slot import Slot
from domain.table import Table
from dto.available_tables import (
    AvailableTablesResponse,
    SlotResponse,
    TableAvailabilityResponse,
)
from enums.slot_status import SlotStatus
from repositories.location_repository import LocationRepository
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository


class TableAvailabilityService:
    """Determine available tables and bookable time slots.

    Orchestrates targeted DynamoDB queries across Table and Slot
    repositories to determine bookable time slots. Slot booking state is
    read directly from the Slot's ``status`` field — no reservation
    lookup is needed.

    All data access uses GSI-backed Query operations — no table scans.

    Filtering logic (all criteria combined with AND):
        1. Location  — only tables whose location_id matches (GSI query).
        2. Capacity  — only tables with capacity >= guests_number.
        3. Date      — only slots on the requested date (GSI query).
        4. from_time (optional) — snap to the first valid slot start >=
           from_time; only tables with that slot FREE qualify; return all
           free slots from that point onwards.
        5. Availability — only slots with ``status == FREE``.

    Query flow (for 3 tables with 7 slots each):
        1 Query  → tables at location           (location_id-index)
        3 Queries → slots per table per date    (table_id-date-index)
       ─────────
        4 total DynamoDB calls, each reading 0–7 items max.
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Create repositories used by this service.

        Args:
            settings: Shared application config.

        """
        cfg = settings or AppConfig()
        self._table_repo = TableRepository(cfg)
        self._slot_repo = SlotRepository(cfg)
        self._location_repo = LocationRepository(cfg)

    def get_available_tables(
        self,
        location_id: UUID | str,
        booking_date: str,
        guests_number: int,
        from_time: Optional[str] = None,
    ) -> AvailableTablesResponse:
        """Return tables with free time slots for the given criteria.

        Args:
            location_id: UUID (or UUID string) of the restaurant location.
            booking_date: Calendar date as "YYYY-MM-DD" (pre-validated).
            guests_number: Minimum table capacity required (pre-validated).
            from_time: Optional filter snapped to the nearest slot start.
                Only tables that have that slot FREE are returned, along
                with all their free slots from that point onwards.

        Returns:
            Response DTO with available tables and their free slots.
            Returns empty tables list when no tables match all criteria.

        """
        logger.info(
            "get_available_tables called",
            location_id=str(location_id),
            date=booking_date,
            guests=guests_number,
            from_time=from_time,
        )

        # ── Step 1: Parse location UUID ──────────────────────────────
        location_uuid = self._parse_uuid(location_id)
        if location_uuid is None:
            return AvailableTablesResponse(tables=[])

        # ── Step 2: Filter by location — query tables at location (GSI)
        location = self._location_repo.get(location_uuid)
        all_tables = self._table_repo.find_by_location_id(location_uuid)

        # ── Step 3: Filter by guest count — capacity >= requested ────
        suitable_tables = [t for t in all_tables if t.capacity >= guests_number]
        logger.info(
            "Capacity filter",
            total_at_location=len(all_tables),
            suitable=len(suitable_tables),
        )

        if not suitable_tables:
            return AvailableTablesResponse(tables=[])

        # ── Step 4: Filter by timeslot — query slots for date (GSI) ──
        table_ids = {t.id for t in suitable_tables}
        slots = self._slot_repo.find_by_table_ids_and_date(table_ids, booking_date)

        if not slots:
            logger.info("No slots found", date=booking_date)
            return AvailableTablesResponse(tables=[])

        # ── Step 5: Snap from_time and qualify tables ────────────────
        if from_time:
            snapped = self._snap_to_slot_start(location.open_time, from_time)
            logger.info("Snapped from_time", from_time=from_time, snapped=str(snapped))

            # Tables must have the snapped slot FREE
            qualifying_ids = {
                s.table_id
                for s in slots
                if s.start_time.time() == snapped and s.status == SlotStatus.FREE
            }
            if not qualifying_ids:
                logger.info("No tables with snapped slot free", snapped=str(snapped))
                return AvailableTablesResponse(tables=[])

            suitable_tables = [t for t in suitable_tables if t.id in qualifying_ids]
            # Keep only slots >= snapped for qualifying tables
            slots = [
                s
                for s in slots
                if s.table_id in qualifying_ids and s.start_time.time() >= snapped
            ]

        # ── Step 6: Filter by availability — keep only FREE slots ────
        free_slots = [s for s in slots if s.status == SlotStatus.FREE]
        logger.info(
            "Availability computed",
            total_slots=len(slots),
            free=len(free_slots),
        )

        # ── Step 7: Build response grouped by table ──────────────────
        return self._build_response(
            suitable_tables,
            free_slots,
            location_address=location.address if location else None,
        )

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID | None:
        """Return UUID value or None when input is not a valid UUID."""
        if isinstance(value, UUID):
            return value

        try:
            return UUID(value)
        except ValueError:
            logger.warning("Invalid UUID", value=value)
            return None

    @staticmethod
    def _snap_to_slot_start(open_time: time, from_time_str: str) -> time:
        """Return the first valid slot start time >= from_time_str.

        Slot schedule starts at ``open_time``; each slot is 90 minutes
        followed by a 15-minute break (105-minute period).

        Args:
            open_time: Location opening time (naive ``datetime.time``).
            from_time_str: Requested filter time as "HH:MM".

        Returns:
            The earliest slot start time that is >= from_time_str.

        """
        from_time = datetime.strptime(from_time_str, "%H:%M").time()
        slot_dt = datetime.combine(date_type.min, open_time)
        target_dt = datetime.combine(date_type.min, from_time)

        while slot_dt < target_dt:
            slot_dt += timedelta(minutes=105)  # 90 min slot + 15 min break

        return slot_dt.time()

    @staticmethod
    def _build_response(
        tables: list[Table],
        free_slots: list[Slot],
        location_address: str | None = None,
    ) -> AvailableTablesResponse:
        """Group free slots by table and build the response DTO.

        Tables with zero free slots are excluded from the response.
        Tables sorted by table_number, slots sorted by start_time.
        """
        table_by_id = {t.id: t for t in tables}

        # Group slots by table
        slots_by_table: dict[UUID, list[SlotResponse]] = {}
        for slot in free_slots:
            if slot.table_id not in table_by_id:
                continue
            sr = SlotResponse(
                slot_id=str(slot.id),
                start_time=slot.start_time.strftime("%H:%M:%S"),
                end_time=slot.end_time.strftime("%H:%M:%S"),
            )
            slots_by_table.setdefault(slot.table_id, []).append(sr)

        # Build table cards (only tables with free slots)
        result: list[TableAvailabilityResponse] = []
        for table_id, slot_list in slots_by_table.items():
            table = table_by_id[table_id]
            slot_list.sort(key=lambda s: s.start_time)
            result.append(
                TableAvailabilityResponse(
                    table_id=str(table.id),
                    table_number=table.table_number,
                    capacity=table.capacity,
                    location_address=location_address,
                    available_slots=slot_list,
                )
            )

        result.sort(key=lambda t: t.table_number)
        return AvailableTablesResponse(tables=result)

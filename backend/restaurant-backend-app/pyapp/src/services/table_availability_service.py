"""Service that computes table availability for a given location and date."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
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
    """Determine available tables and free slots for a location/date filter."""

    def __init__(
        self,
        settings: AppConfig | None = None,
        table_repository: TableRepository | None = None,
        slot_repository: SlotRepository | None = None,
        location_repository: LocationRepository | None = None,
    ) -> None:
        """Initialize repositories, using defaults when omitted."""
        cfg = settings or AppConfig()
        self._table_repo = table_repository or TableRepository(cfg)
        self._slot_repo = slot_repository or SlotRepository(cfg)
        self._location_repo = location_repository or LocationRepository(cfg)

    def get_available_tables(
        self,
        location_id: UUID | str,
        booking_date: str,
        guests_number: int,
        from_time: Optional[str] = None,
    ) -> AvailableTablesResponse:
        """Return tables with free slots for location/date/guest filters."""
        logger.info(
            "get_available_tables called",
            location_id=str(location_id),
            date=booking_date,
            guests=guests_number,
            from_time=from_time,
        )
        now_utc = datetime.now(timezone.utc)
        is_today = booking_date == now_utc.date().isoformat()

        try:
            location_uuid = (
                location_id if isinstance(location_id, UUID) else UUID(location_id)
            )
        except (TypeError, ValueError):
            logger.warning("Invalid UUID", value=location_id)
            return AvailableTablesResponse(tables=[])

        location = self._location_repo.get(location_uuid)
        all_tables = self._table_repo.find_by_location_id(location_uuid)

        suitable_tables = [t for t in all_tables if t.capacity >= guests_number]
        logger.info(
            "Capacity filter",
            total_at_location=len(all_tables),
            suitable=len(suitable_tables),
        )

        if not suitable_tables:
            return AvailableTablesResponse(tables=[])

        table_ids = {t.id for t in suitable_tables}
        slots = self._slot_repo.find_by_table_ids_and_date(table_ids, booking_date)

        if not slots:
            logger.info("No slots found", date=booking_date)
            return AvailableTablesResponse(tables=[])

        effective_from_time = from_time
        if not effective_from_time and is_today:
            future_slots = [
                s
                for s in slots
                if s.status == SlotStatus.FREE and s.start_time > now_utc
            ]
            if not future_slots:
                logger.info("No future free slots for today", date=booking_date)
                return AvailableTablesResponse(tables=[])
            effective_from_time = self._format_utc(
                min(future_slots, key=lambda s: s.start_time).start_time
            )
            logger.info(
                "Auto-selected next free slot for today",
                date=booking_date,
                auto_from_time=effective_from_time,
            )

        if effective_from_time:
            requested_time = self._extract_requested_time(effective_from_time)
            snapped = self._snap_to_slot_start(location.open_time, requested_time)
            logger.info(
                "Snapped from_time",
                from_time=effective_from_time,
                snapped=str(snapped),
            )

            if is_today:
                snapped_dt = datetime.combine(
                    now_utc.date(), snapped, tzinfo=timezone.utc
                )
                if snapped_dt <= now_utc:
                    logger.info(
                        "Snapped slot is in the past for today",
                        snapped=str(snapped),
                        now=now_utc.isoformat(),
                    )
                    return AvailableTablesResponse(tables=[])

            qualifying_ids = {
                s.table_id
                for s in slots
                if s.start_time.time() == snapped and s.status == SlotStatus.FREE
            }
            if not qualifying_ids:
                logger.info("No tables with snapped slot free", snapped=str(snapped))
                return AvailableTablesResponse(tables=[])

            suitable_tables = [t for t in suitable_tables if t.id in qualifying_ids]
            slots = [
                s
                for s in slots
                if s.table_id in qualifying_ids and s.start_time.time() >= snapped
            ]

        free_slots = [s for s in slots if s.status == SlotStatus.FREE]
        before_filter = len(free_slots)
        if is_today:
            free_slots = [s for s in free_slots if s.start_time > now_utc]
            logger.info(
                "Filtered out past slots for today",
                before_filter=before_filter,
                after_filter=len(free_slots),
            )
        logger.info(
            "Availability computed",
            total_slots=len(slots),
            free=len(free_slots),
        )

        return self._build_response(
            suitable_tables,
            free_slots,
            location_address=location.address if location else None,
        )

    def get_valid_slot_start_times(
        self,
        location_id: UUID,
        booking_date: str | None = None,
    ) -> list[str]:
        """Return distinct free slot start times for a location and date."""
        date_iso = booking_date or datetime.now(timezone.utc).date().isoformat()
        slots = self._get_free_slots_for_location(location_id, date_iso)

        now_utc = datetime.now(timezone.utc)
        is_today = date_iso == now_utc.date().isoformat()
        if is_today:
            slots = [slot for slot in slots if slot.start_time > now_utc]

        start_times = sorted({slot.start_time for slot in slots})
        return [self._format_utc(dt) for dt in start_times]

    def get_valid_slot_end_times(
        self,
        location_id: UUID,
        booking_date: str | None = None,
        start_time: str | None = None,
    ) -> list[str]:
        """Return distinct free slot end times for a location and date."""
        date_iso = booking_date or datetime.now(timezone.utc).date().isoformat()
        slots = self._get_free_slots_for_location(location_id, date_iso)

        now_utc = datetime.now(timezone.utc)
        is_today = date_iso == now_utc.date().isoformat()
        if is_today:
            slots = [slot for slot in slots if slot.start_time > now_utc]

        if start_time:
            start_dt = self._parse_utc_datetime(start_time, date_iso)
            slots = [slot for slot in slots if slot.start_time >= start_dt]

        end_times = sorted({slot.end_time for slot in slots})
        return [self._format_utc(dt) for dt in end_times]

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _snap_to_slot_start(open_time: time, requested_time: time) -> time:
        """Return earliest slot start not earlier than requested_time."""
        slot_dt = datetime.combine(date_type.min, open_time)
        target_dt = datetime.combine(date_type.min, requested_time)

        while slot_dt < target_dt:
            slot_dt += timedelta(minutes=105)

        return slot_dt.time()

    def _get_free_slots_for_location(
        self, location_id: UUID, date_iso: str
    ) -> list[Slot]:
        """Load FREE slots for all tables in location on the requested date."""
        tables = self._table_repo.find_by_location_id(location_id)
        if not tables:
            return []

        table_ids = {table.id for table in tables}
        slots = self._slot_repo.find_by_table_ids_and_date(table_ids, date_iso)
        return [slot for slot in slots if slot.status == SlotStatus.FREE]

    @staticmethod
    def _parse_utc_datetime(value: str, date_iso: str) -> datetime:
        """Parse an incoming UTC datetime (or HH:MM) into aware datetime."""
        normalized = value.strip()
        if "T" in normalized:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)

        parsed_time = time.fromisoformat(normalized)
        return datetime.combine(
            date_type.fromisoformat(date_iso),
            parsed_time,
            tzinfo=timezone.utc,
        )

    @staticmethod
    def _extract_requested_time(from_time_value: str) -> time:
        """Parse requested time from a UTC datetime string."""
        parsed = datetime.fromisoformat(from_time_value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).time()

    @staticmethod
    def _format_utc(dt: datetime) -> str:
        """Format datetime as UTC ISO string with trailing Z."""
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _build_response(
        tables: list[Table],
        free_slots: list[Slot],
        location_address: str | None = None,
    ) -> AvailableTablesResponse:
        """Group free slots by table and build response."""
        table_by_id = {t.id: t for t in tables}

        slots_by_table: dict[UUID, list[SlotResponse]] = {}
        for slot in free_slots:
            if slot.table_id not in table_by_id:
                continue
            sr = SlotResponse(
                slot_id=str(slot.id),
                start_time=TableAvailabilityService._format_utc(slot.start_time),
                end_time=TableAvailabilityService._format_utc(slot.end_time),
            )
            slots_by_table.setdefault(slot.table_id, []).append(sr)

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

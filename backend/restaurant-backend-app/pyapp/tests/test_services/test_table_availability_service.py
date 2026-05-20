"""Unit tests for TableAvailabilityService filtering behavior."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.slot import Slot  # type: ignore[import-untyped]
    from domain.table import Table  # type: ignore[import-untyped]
    from enums.slot_status import SlotStatus  # type: ignore[import-untyped]
    from services.table_availability_service import (  # type: ignore[import-untyped]
        TableAvailabilityService,
    )

_LOCATION_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TABLE_1_ID = UUID("11111111-1111-1111-1111-111111111111")
_TABLE_2_ID = UUID("22222222-2222-2222-2222-222222222222")
_SLOT_1_ID = UUID("33333333-3333-3333-3333-333333333333")
_SLOT_2_ID = UUID("44444444-4444-4444-4444-444444444444")


def _dt(hour: int, minute: int) -> datetime:
    """Build an aware UTC datetime for deterministic slot fixtures."""
    return datetime(2026, 5, 20, hour, minute, tzinfo=timezone.utc)


def _table(table_id: UUID, table_number: int, capacity: int) -> Table:
    """Build a Table fixture bound to the same location."""
    return Table(
        id=table_id,
        table_number=table_number,
        capacity=capacity,
        location_id=_LOCATION_ID,
    )


def _slot(
    slot_id: UUID,
    table_id: UUID,
    h: int,
    m: int,
    status: SlotStatus = SlotStatus.FREE,
) -> Slot:
    """Build a Slot fixture for the given table, start time, and status."""
    start = _dt(h, m)
    end = _dt(h + 1, (m + 30) % 60)
    return Slot(
        id=slot_id,
        table_id=table_id,
        start_time=start,
        end_time=end,
        date=_dt(0, 0),
        status=status,
    )


class TestTableAvailabilityService(unittest.TestCase):
    """Verify location/capacity/time/status filters in service orchestration."""

    def setUp(self) -> None:
        """Create service instance with mocked repositories."""
        self.service = TableAvailabilityService.__new__(TableAvailabilityService)
        self.service._table_repo = MagicMock()
        self.service._slot_repo = MagicMock()
        self.service._location_repo = MagicMock()
        location = MagicMock()
        location.name = "48 Rustaveli Avenue, Tbilisi"
        self.service._location_repo.get.return_value = location

    def test_invalid_location_uuid_returns_empty_without_repo_calls(self) -> None:
        """Invalid UUID input should short-circuit and return an empty response."""
        response = self.service.get_available_tables(
            location_id="not-a-uuid",
            booking_date="2026-05-20",
            guests_number=4,
        )

        self.assertEqual(response.model_dump(), {"tables": []})
        self.service._table_repo.find_by_location_id.assert_not_called()
        self.service._slot_repo.find_by_table_ids_and_date.assert_not_called()

    def test_filters_by_capacity_and_time_window(self) -> None:
        """Only tables/slots that satisfy all criteria must be returned."""
        small_table = _table(_TABLE_1_ID, table_number=1, capacity=2)
        big_table = _table(_TABLE_2_ID, table_number=2, capacity=6)
        morning = _slot(_SLOT_1_ID, _TABLE_2_ID, 10, 0)
        afternoon = _slot(_SLOT_2_ID, _TABLE_2_ID, 15, 0)

        self.service._table_repo.find_by_location_id.return_value = [
            small_table,
            big_table,
        ]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            morning,
            afternoon,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=4,
            from_time="14:00",
            to_time="17:00",
        )

        data = response.model_dump()
        self.assertEqual(len(data["tables"]), 1)
        self.assertEqual(data["tables"][0]["table_id"], str(_TABLE_2_ID))
        self.assertEqual(len(data["tables"][0]["available_slots"]), 1)
        self.assertEqual(
            data["tables"][0]["available_slots"][0]["slot_id"], str(_SLOT_2_ID)
        )

        self.service._slot_repo.find_by_table_ids_and_date.assert_called_once_with(
            {_TABLE_2_ID}, "2026-05-20"
        )

    def test_excludes_reserved_slots_and_returns_empty_when_none_free(self) -> None:
        """Slots with status != FREE must be removed from the response."""
        table = _table(_TABLE_1_ID, table_number=1, capacity=4)
        slot = _slot(_SLOT_1_ID, _TABLE_1_ID, 12, 0, status=SlotStatus.RESERVED)

        self.service._table_repo.find_by_location_id.return_value = [table]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [slot]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
        )

        self.assertEqual(response.model_dump(), {"tables": []})

    def test_returns_empty_when_no_tables_match_capacity(self) -> None:
        """Capacity filter should return empty without querying slots."""
        self.service._table_repo.find_by_location_id.return_value = [
            _table(_TABLE_1_ID, table_number=1, capacity=2)
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=6,
        )

        self.assertEqual(response.model_dump(), {"tables": []})
        self.service._slot_repo.find_by_table_ids_and_date.assert_not_called()

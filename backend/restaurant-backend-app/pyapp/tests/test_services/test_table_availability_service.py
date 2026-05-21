"""Unit tests for TableAvailabilityService filtering behavior."""

from __future__ import annotations

import unittest
from datetime import datetime, time, timedelta, timezone
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
_SLOT_3_ID = UUID("55555555-5555-5555-5555-555555555555")
_SLOT_4_ID = UUID("66666666-6666-6666-6666-666666666666")

# Location opens at 12:00 → slot schedule: 12:00, 13:45, 15:30, 17:15 …
_OPEN_TIME = time(12, 0)


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
    """Build a Slot fixture for the given table, start time, and status.

    End time is start + 90 minutes (standard slot duration).
    """
    start = _dt(h, m)
    end = start + timedelta(minutes=90)
    return Slot(
        id=slot_id,
        table_id=table_id,
        start_time=start,
        end_time=end,
        date=_dt(0, 0),
        status=status,
    )


class TestSnapToSlotStart(unittest.TestCase):
    """Unit tests for the _snap_to_slot_start static helper."""

    def test_from_time_exactly_on_slot_boundary_returns_same_time(self) -> None:
        """When from_time equals a slot start, it should be returned unchanged."""
        # open_time=12:00 → slots at 12:00, 13:45, 15:30 …
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="12:00"
        )
        self.assertEqual(result, time(12, 0))

    def test_from_time_between_slots_snaps_up_to_next_slot(self) -> None:
        """12:57 is between 12:00 and 13:45, so should snap to 13:45."""
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="12:57"
        )
        self.assertEqual(result, time(13, 45))

    def test_from_time_exactly_on_second_slot_returns_second_slot(self) -> None:
        """13:45 is exactly the second slot start; should return 13:45."""
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="13:45"
        )
        self.assertEqual(result, time(13, 45))

    def test_from_time_just_after_second_slot_snaps_to_third(self) -> None:
        """13:46 is just past 13:45, should snap forward to 15:30."""
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="13:46"
        )
        self.assertEqual(result, time(15, 30))

    def test_different_open_time(self) -> None:
        """Snap correctly when the location opens at a non-standard time."""
        # open_time=09:00 → slots at 09:00, 10:45, 12:30 …
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(9, 0), from_time_str="11:00"
        )
        self.assertEqual(result, time(12, 30))


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
        location.address = "48 Rustaveli Avenue, Tbilisi"
        location.open_time = _OPEN_TIME  # 12:00
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

    def test_no_from_time_returns_all_free_slots(self) -> None:
        """Without from_time all FREE slots for all suitable tables are returned."""
        table = _table(_TABLE_1_ID, table_number=1, capacity=4)
        # Slots at 12:00, 13:45, 15:30 (all valid schedule times)
        s1 = _slot(_SLOT_1_ID, _TABLE_1_ID, 12, 0)
        s2 = _slot(_SLOT_2_ID, _TABLE_1_ID, 13, 45)
        s3 = _slot(_SLOT_3_ID, _TABLE_1_ID, 15, 30)

        self.service._table_repo.find_by_location_id.return_value = [table]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [s1, s2, s3]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
        )

        data = response.model_dump()
        self.assertEqual(len(data["tables"]), 1)
        self.assertEqual(len(data["tables"][0]["available_slots"]), 3)

    def test_from_time_on_slot_boundary_qualifies_table_and_returns_later_slots(
        self,
    ) -> None:
        """from_time=13:45 snaps to 13:45; only tables with that slot FREE qualify.

        All free slots >= 13:45 are returned for the qualifying table.
        """
        # Table 1: has 13:45 FREE + 15:30 FREE → qualifies
        # Table 2: does NOT have 13:45 at all → excluded
        table1 = _table(_TABLE_1_ID, table_number=1, capacity=4)
        table2 = _table(_TABLE_2_ID, table_number=2, capacity=4)

        s1_early = _slot(_SLOT_1_ID, _TABLE_1_ID, 12, 0)  # before filter
        s1_snap = _slot(_SLOT_2_ID, _TABLE_1_ID, 13, 45)  # at snapped start
        s1_later = _slot(_SLOT_3_ID, _TABLE_1_ID, 15, 30)  # after snapped start
        s2_later = _slot(_SLOT_4_ID, _TABLE_2_ID, 15, 30)  # table2 has no 13:45 slot

        self.service._table_repo.find_by_location_id.return_value = [table1, table2]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            s1_early,
            s1_snap,
            s1_later,
            s2_later,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
            from_time="13:45",
        )

        self.assertEqual(len(response.tables), 1)
        self.assertEqual(response.tables[0].table_id, str(_TABLE_1_ID))
        slot_times = [s.start_time for s in response.tables[0].available_slots]
        self.assertIn("13:45:00", slot_times)
        self.assertIn("15:30:00", slot_times)
        self.assertNotIn("12:00:00", slot_times)

    def test_from_time_between_slots_snaps_up_and_filters_correctly(self) -> None:
        """from_time=12:57 is between 12:00 and 13:45; snaps to 13:45.

        Only tables with a FREE slot at 13:45 qualify; slots before 13:45
        must not appear in the response.
        """
        table = _table(_TABLE_1_ID, table_number=1, capacity=4)
        s_before = _slot(_SLOT_1_ID, _TABLE_1_ID, 12, 0)  # before snapped time
        s_snap = _slot(_SLOT_2_ID, _TABLE_1_ID, 13, 45)  # at snapped time
        s_after = _slot(_SLOT_3_ID, _TABLE_1_ID, 15, 30)  # after snapped time

        self.service._table_repo.find_by_location_id.return_value = [table]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            s_before,
            s_snap,
            s_after,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
            from_time="12:57",
        )

        self.assertEqual(len(response.tables), 1)
        slot_times = [s.start_time for s in response.tables[0].available_slots]
        self.assertEqual(slot_times, ["13:45:00", "15:30:00"])

    def test_snapped_slot_reserved_returns_empty(self) -> None:
        """If the snapped slot is RESERVED the table must not qualify."""
        table = _table(_TABLE_1_ID, table_number=1, capacity=4)
        # 13:45 is RESERVED — table should not qualify
        s_snap = _slot(_SLOT_1_ID, _TABLE_1_ID, 13, 45, status=SlotStatus.RESERVED)
        s_after = _slot(_SLOT_2_ID, _TABLE_1_ID, 15, 30)

        self.service._table_repo.find_by_location_id.return_value = [table]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            s_snap,
            s_after,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
            from_time="13:45",
        )

        self.assertEqual(response.model_dump(), {"tables": []})

    def test_later_slots_with_reserved_status_excluded_from_response(self) -> None:
        """Snapped slot is FREE (table qualifies) but later RESERVED slots are hidden."""
        table = _table(_TABLE_1_ID, table_number=1, capacity=4)
        s_snap = _slot(_SLOT_1_ID, _TABLE_1_ID, 13, 45)  # FREE
        s_reserved = _slot(
            _SLOT_2_ID, _TABLE_1_ID, 15, 30, SlotStatus.RESERVED
        )  # RESERVED
        s_free = _slot(_SLOT_3_ID, _TABLE_1_ID, 17, 15)  # FREE

        self.service._table_repo.find_by_location_id.return_value = [table]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            s_snap,
            s_reserved,
            s_free,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=2,
            from_time="13:45",
        )

        slot_times = [s.start_time for s in response.tables[0].available_slots]
        self.assertEqual(slot_times, ["13:45:00", "17:15:00"])

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

    def test_capacity_filter_excludes_small_table(self) -> None:
        """A table smaller than guests_number must never appear in the response."""
        small_table = _table(_TABLE_1_ID, table_number=1, capacity=2)
        big_table = _table(_TABLE_2_ID, table_number=2, capacity=6)
        # Both tables share the same slot time; only big_table should qualify
        s_small = _slot(_SLOT_1_ID, _TABLE_1_ID, 13, 45)
        s_big = _slot(_SLOT_2_ID, _TABLE_2_ID, 13, 45)

        self.service._table_repo.find_by_location_id.return_value = [
            small_table,
            big_table,
        ]
        self.service._slot_repo.find_by_table_ids_and_date.return_value = [
            s_small,
            s_big,
        ]

        response = self.service.get_available_tables(
            location_id=_LOCATION_ID,
            booking_date="2026-05-20",
            guests_number=4,
            from_time="13:45",
        )

        self.assertEqual(len(response.tables), 1)
        self.assertEqual(response.tables[0].table_id, str(_TABLE_2_ID))

        self.service._slot_repo.find_by_table_ids_and_date.assert_called_once_with(
            {_TABLE_2_ID}, "2026-05-20"
        )

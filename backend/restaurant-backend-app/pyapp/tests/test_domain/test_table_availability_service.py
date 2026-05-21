"""Tests for TableAvailabilityService business flow and response shaping."""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.slot import Slot
    from domain.table import Table
    from enums.slot_status import SlotStatus
    from services.table_availability_service import TableAvailabilityService

_LOCATION_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TABLE_1_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_TABLE_2_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_SLOT_1_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_SLOT_2_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
_SLOT_3_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")
_BOOKING_DATE = "2026-05-16"


def _aware(h: int, m: int) -> datetime:
    """Return an aware datetime for test slots."""
    return datetime(2026, 5, 16, h, m, tzinfo=timezone.utc)


def _table(table_id: uuid.UUID, number: int, cap: int) -> Table:
    """Build a Table model with shared location for tests."""
    return Table(
        id=table_id,
        table_number=number,
        capacity=cap,
        location_id=_LOCATION_ID,
    )


def _slot(
    slot_id: uuid.UUID,
    table_id: uuid.UUID,
    start_h: int,
    start_m: int,
    status: SlotStatus = SlotStatus.FREE,
) -> Slot:
    """Build a Slot model for tests."""
    start = _aware(start_h, start_m)
    return Slot(
        id=slot_id,
        table_id=table_id,
        start_time=start,
        end_time=start.replace(hour=start.hour + 1, minute=(start.minute + 30) % 60),
        date=_aware(0, 0),
        status=status,
    )


class TestTableAvailabilityService(unittest.TestCase):
    """Tests for orchestrating repositories and shaping available table responses."""

    def setUp(self) -> None:
        """Patch repository classes and wire mock instances into the service."""
        table_repo_patcher = patch(
            "services.table_availability_service.TableRepository"
        )
        slot_repo_patcher = patch("services.table_availability_service.SlotRepository")
        location_repo_patcher = patch(
            "services.table_availability_service.LocationRepository"
        )

        self.mock_table_repo_cls = table_repo_patcher.start()
        self.mock_slot_repo_cls = slot_repo_patcher.start()
        self.mock_location_repo_cls = location_repo_patcher.start()

        self.addCleanup(table_repo_patcher.stop)
        self.addCleanup(slot_repo_patcher.stop)
        self.addCleanup(location_repo_patcher.stop)

        self.mock_table_repo = MagicMock()
        self.mock_slot_repo = MagicMock()
        self.mock_location_repo = MagicMock()

        self.mock_table_repo_cls.return_value = self.mock_table_repo
        self.mock_slot_repo_cls.return_value = self.mock_slot_repo
        self.mock_location_repo_cls.return_value = self.mock_location_repo

        location = MagicMock()
        location.name = "48 Rustaveli Avenue, Tbilisi"
        self.mock_location_repo.get.return_value = location

        self.service = TableAvailabilityService()

    def test_invalid_location_uuid_returns_empty_response(self) -> None:
        """Invalid UUID must short-circuit and skip all repository calls."""
        response = self.service.get_available_tables("not-a-uuid", _BOOKING_DATE, 2)
        self.assertEqual(response.tables, [])
        self.mock_table_repo.find_by_location_id.assert_not_called()
        self.mock_slot_repo.find_by_table_ids_and_date.assert_not_called()

    def test_no_tables_with_required_capacity_returns_empty_response(self) -> None:
        """When no table capacity fits guests_number, result must be empty."""
        self.mock_table_repo.find_by_location_id.return_value = [
            _table(_TABLE_1_ID, 1, 2),
            _table(_TABLE_2_ID, 2, 2),
        ]

        response = self.service.get_available_tables(
            str(_LOCATION_ID), _BOOKING_DATE, 4
        )

        self.assertEqual(response.tables, [])
        self.mock_slot_repo.find_by_table_ids_and_date.assert_not_called()

    def test_no_slots_returns_empty_response(self) -> None:
        """When no slots exist for suitable tables on that date, result must be empty."""
        self.mock_table_repo.find_by_location_id.return_value = [
            _table(_TABLE_1_ID, 1, 4),
        ]
        self.mock_slot_repo.find_by_table_ids_and_date.return_value = []

        response = self.service.get_available_tables(
            str(_LOCATION_ID), _BOOKING_DATE, 2
        )

        self.assertEqual(response.tables, [])

    def test_excludes_reserved_slots_and_sorts_result(self) -> None:
        """Slots with non-FREE status must be excluded; output is sorted."""
        table_2 = _table(_TABLE_2_ID, 2, 6)
        table_1 = _table(_TABLE_1_ID, 1, 4)

        slot_late = _slot(_SLOT_2_ID, _TABLE_1_ID, 12, 0)
        slot_early = _slot(_SLOT_1_ID, _TABLE_1_ID, 10, 0)
        slot_other_table = _slot(
            _SLOT_3_ID, _TABLE_2_ID, 11, 0, status=SlotStatus.RESERVED
        )

        self.mock_table_repo.find_by_location_id.return_value = [table_2, table_1]
        self.mock_slot_repo.find_by_table_ids_and_date.return_value = [
            slot_late,
            slot_other_table,
            slot_early,
        ]

        response = self.service.get_available_tables(
            str(_LOCATION_ID), _BOOKING_DATE, 4
        )

        # table 2 had only a reserved slot, so only table 1 remains
        self.assertEqual(len(response.tables), 1)
        self.assertEqual(response.tables[0].table_number, 1)
        self.assertEqual(len(response.tables[0].available_slots), 2)

        # slots must be ordered by start_time: 10:00 then 12:00
        self.assertEqual(
            response.tables[0].available_slots[0].slot_id,
            str(_SLOT_1_ID),
        )
        self.assertEqual(
            response.tables[0].available_slots[1].slot_id,
            str(_SLOT_2_ID),
        )

        self.mock_table_repo.find_by_location_id.assert_called_once_with(_LOCATION_ID)
        self.mock_slot_repo.find_by_table_ids_and_date.assert_called_once()


class TestTableAvailabilityServiceDomain(unittest.TestCase):
    """Test TableAvailabilityService slot-start snapping logic."""

    def setUp(self) -> None:
        """Create mocked service for testing snap-to-slot-start behavior."""
        self.service = TableAvailabilityService()
        self.service._table_repo = MagicMock()
        self.service._slot_repo = MagicMock()
        self.service._location_repo = MagicMock()

    def test_snap_to_slot_start_exact_boundary(self):
        """_snap_to_slot_start returns from_time unchanged when it is already a slot start."""
        from datetime import time

        # open_time=12:00 → slots at 12:00, 13:45, 15:30 …
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="12:00"
        )
        self.assertEqual(result, time(12, 0))

    def test_snap_to_slot_start_snaps_up_to_next_boundary(self):
        """_snap_to_slot_start advances to the next slot when from_time is between starts."""
        from datetime import time

        # open_time=12:00, from_time=12:57 → must snap to 13:45
        result = TableAvailabilityService._snap_to_slot_start(
            open_time=time(12, 0), from_time_str="12:57"
        )
        self.assertEqual(result, time(13, 45))

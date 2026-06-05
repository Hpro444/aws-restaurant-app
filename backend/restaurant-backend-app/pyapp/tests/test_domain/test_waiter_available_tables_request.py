"""Tests for WaiterAvailableTablesRequest validation rules."""

import unittest
from datetime import datetime as dt
from datetime import timedelta, timezone

from pyapp.tests import ImportFromSourceContext
from pydantic import ValidationError

with ImportFromSourceContext():
    from dto.available_tables import WaiterAvailableTablesRequest


class TestWaiterAvailableTablesRequest(unittest.TestCase):
    """Covers the request validators as isolated unit tests."""

    def setUp(self) -> None:
        """Build a reusable valid payload for each case."""
        self.today = dt.now(timezone.utc).date()
        self.base_payload = {
            "location_id": "11111111-1111-1111-1111-111111111111",
            "date": self.today.isoformat(),
            "guests_number": 4,
            "from_time": f"{self.today.isoformat()}T12:00:00Z",
            "to_time": f"{self.today.isoformat()}T16:00:00Z",
        }

    def test_default_date_validator_fills_today_when_missing(self) -> None:
        """Date should default to today's UTC date when omitted."""
        payload = {k: v for k, v in self.base_payload.items() if k != "date"}

        request = WaiterAvailableTablesRequest(**payload)

        self.assertEqual(request.date, self.today.isoformat())

    def test_time_validator_normalizes_trailing_z(self) -> None:
        """from_time and to_time should be normalized to UTC ISO strings."""
        request = WaiterAvailableTablesRequest(**self.base_payload)

        self.assertEqual(request.from_time, self.base_payload["from_time"])
        self.assertEqual(request.to_time, self.base_payload["to_time"])

    def test_invalid_time_order_raises_validation_error(self) -> None:
        """from_time must be earlier than to_time."""
        payload = {
            **self.base_payload,
            "from_time": f"{self.today.isoformat()}T16:00:00Z",
            "to_time": f"{self.today.isoformat()}T12:00:00Z",
        }

        with self.assertRaises(ValidationError):
            WaiterAvailableTablesRequest(**payload)

    def test_past_date_is_rejected(self) -> None:
        """The request must not accept dates in the past."""
        payload = {
            **self.base_payload,
            "date": (self.today - timedelta(days=1)).isoformat(),
            "from_time": f"{(self.today - timedelta(days=1)).isoformat()}T12:00:00Z",
            "to_time": f"{(self.today - timedelta(days=1)).isoformat()}T16:00:00Z",
        }

        with self.assertRaises(ValidationError):
            WaiterAvailableTablesRequest(**payload)

"""Tests for ReservationWaiterView key synthesis and serialization."""

import unittest
import uuid

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.reservation_waiter_view import (  # type: ignore[import-untyped]
        ReservationWaiterView,
    )
    from enums import ReservationStatus  # type: ignore[import-untyped]

_RES_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_CUST_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
_WAITER_ID = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_LOC_ID = uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")


def _make_view(**overrides) -> ReservationWaiterView:
    """Return a ReservationWaiterView with sensible defaults, allowing overrides."""
    fields = {
        "id": _RES_ID,
        "customer_id": _CUST_ID,
        "waiter_id": _WAITER_ID,
        "location_id": _LOC_ID,
        "location_address": "1 Freedom Square, Tbilisi",
        "table_number": 5,
        "table_name": "5",
        "date": "2026-05-16",
        "time_from": "12:00",
        "time_to": "13:30",
        "guests_number": 4,
        "status": ReservationStatus.RESERVED,
    }
    fields.update(overrides)
    return ReservationWaiterView(**fields)


class TestKeyHelpers(unittest.TestCase):
    """Tests for the GSI key-building static helpers."""

    def test_location_date_joins_with_hash(self) -> None:
        """location_date must be ``location_id#date``."""
        self.assertEqual(
            ReservationWaiterView.location_date(_LOC_ID, "2026-05-16"),
            f"{_LOC_ID}#2026-05-16",
        )

    def test_time_table_joins_with_hash(self) -> None:
        """time_table must be ``time_to#table_name`` (end time, for active-at queries)."""
        self.assertEqual(
            ReservationWaiterView.time_table("13:30", "5"),
            "13:30#5",
        )


class TestToDynamoItem(unittest.TestCase):
    """Tests for ReservationWaiterView.to_dynamodb_item key injection."""

    def setUp(self) -> None:
        """Serialize a representative view once per test."""
        self.view = _make_view()
        self.item = self.view.to_dynamodb_item()

    def test_injects_location_date_partition_attribute(self) -> None:
        """The GSI partition attribute must be synthesized into the item."""
        self.assertEqual(self.item["location_date"], {"S": f"{_LOC_ID}#2026-05-16"})

    def test_injects_time_table_sort_attribute(self) -> None:
        """The GSI sort attribute must be synthesized from the end time."""
        self.assertEqual(self.item["time_table"], {"S": "13:30#5"})

    def test_id_serialized_as_s(self) -> None:
        """The reservation id is stored as the DynamoDB partition key string."""
        self.assertEqual(self.item["id"], {"S": str(_RES_ID)})


class TestRoundTrip(unittest.TestCase):
    """Tests that synthetic GSI attributes do not break deserialization."""

    def test_round_trip_ignores_synthetic_key_attributes(self) -> None:
        """from_dynamodb_item must drop location_date/time_table and restore the model."""
        view = _make_view()
        restored = ReservationWaiterView.from_dynamodb_item(view.to_dynamodb_item())
        self.assertEqual(restored, view)

    def test_round_trip_preserves_optional_none(self) -> None:
        """A null customer_id must round-trip back to None."""
        view = _make_view(customer_id=None)
        restored = ReservationWaiterView.from_dynamodb_item(view.to_dynamodb_item())
        self.assertIsNone(restored.customer_id)

    def test_deserializes_item_with_omitted_nullable_attributes(self) -> None:
        """A seeded visitor row omits None attributes; it must still deserialize.

        The seeder writes projection rows with ``exclude_none=True``, so a visitor
        booking (``customer_id`` is None) has no ``customer_id`` attribute at all.
        Such rows must deserialize with the nullable fields defaulting to None
        rather than raising a validation error (previously a 500 on the waiter view).
        """
        item = _make_view().to_dynamodb_item()
        for attr in ("customer_id", "waiter_id", "location_address", "table_number"):
            item.pop(attr, None)

        restored = ReservationWaiterView.from_dynamodb_item(item)

        self.assertIsNone(restored.customer_id)
        self.assertIsNone(restored.waiter_id)
        self.assertIsNone(restored.location_address)
        self.assertIsNone(restored.table_number)
        self.assertEqual(restored.id, _RES_ID)


if __name__ == "__main__":
    unittest.main()

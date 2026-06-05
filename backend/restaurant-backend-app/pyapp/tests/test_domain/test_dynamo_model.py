"""Tests for DynamoModel serialization, deserialization, and _exclude_none behaviour."""

import unittest
import uuid
from datetime import datetime, timezone

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.dish import Dish
    from domain.login_attempts import LoginAttempts
    from domain.reservation import Reservation
    from enums.reservation_status import ReservationStatus

_DISH_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_LOCATION_ID = uuid.UUID("87654321-4321-8765-4321-876543218765")
_RESERVATION_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_WAITER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_SLOT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_CREATED_AT = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_dish(**overrides) -> Dish:
    """Return a Dish with sensible defaults, allowing field overrides."""
    return Dish(
        id=_DISH_ID,
        location_id=_LOCATION_ID,
        name="Margherita",
        description="Classic pizza",
        image_url="https://example.com/pizza.jpg",
        price=12.99,
        weight_gram=350,
        specialty=False,
        popular=True,
        **overrides,
    )


def _make_reservation(**overrides) -> Reservation:
    """Return a Reservation with sensible defaults, allowing field overrides."""
    return Reservation(
        id=_RESERVATION_ID,
        customer_id=None,
        waiter_id=_WAITER_ID,
        created_at=_CREATED_AT,
        slot_ids=[_SLOT_ID],
        status=ReservationStatus.RESERVED,
        number_of_guests=4,
        **overrides,
    )


class TestDishToItem(unittest.TestCase):
    """Tests for Dish.to_dynamodb_item — field-type mapping."""

    def setUp(self) -> None:
        """Create a Dish and its serialized form once per test."""
        self.dish = _make_dish()
        self.item = self.dish.to_dynamodb_item()

    def test_uuid_serialized_as_s(self) -> None:
        """UUID fields must be stored as DynamoDB S (string)."""
        self.assertEqual(self.item["id"], {"S": str(_DISH_ID)})
        self.assertEqual(self.item["location_id"], {"S": str(_LOCATION_ID)})

    def test_string_field_serialized_as_s(self) -> None:
        """Plain string fields must be stored as DynamoDB S."""
        self.assertEqual(self.item["name"], {"S": "Margherita"})

    def test_float_serialized_as_n(self) -> None:
        """Float fields must be stored as DynamoDB N."""
        self.assertEqual(self.item["price"], {"N": "12.99"})

    def test_int_serialized_as_n(self) -> None:
        """Int fields must be stored as DynamoDB N."""
        self.assertEqual(self.item["weight_gram"], {"N": "350"})


class TestDishFromItem(unittest.TestCase):
    """Tests for Dish.from_dynamodb_item — type coercion and Decimal handling."""

    def setUp(self) -> None:
        """Prepare a raw DynamoDB-style item for reuse across tests."""
        self.dish = _make_dish()
        self.raw_item = self.dish.to_dynamodb_item()

    def test_round_trip(self) -> None:
        """Serializing then deserializing a Dish must return an equal instance."""
        restored = Dish.from_dynamodb_item(self.raw_item)
        self.assertEqual(restored, self.dish)

    def test_decimal_int_coerced_to_int(self) -> None:
        """Decimal from TypeDeserializer must be converted to int for int fields."""
        restored = Dish.from_dynamodb_item(self.raw_item)
        self.assertIsInstance(restored.weight_gram, int)

    def test_decimal_float_coerced_to_float(self) -> None:
        """Decimal from TypeDeserializer must be converted to float for float fields."""
        restored = Dish.from_dynamodb_item(self.raw_item)
        self.assertIsInstance(restored.price, float)
        self.assertAlmostEqual(restored.price, 12.99)

    def test_uuid_string_coerced_to_uuid(self) -> None:
        """String UUIDs returned by TypeDeserializer must be coerced to UUID objects."""
        restored = Dish.from_dynamodb_item(self.raw_item)
        self.assertIsInstance(restored.id, uuid.UUID)
        self.assertEqual(restored.id, _DISH_ID)


class TestReservationSerialization(unittest.TestCase):
    """Tests for Reservation optional UUIDs, AwareDatetime, and enum serialization."""

    def setUp(self) -> None:
        """Create a Reservation with customer_id=None and its serialized item."""
        self.reservation = _make_reservation()
        self.item = self.reservation.to_dynamodb_item()

    def test_none_uuid_serialized_as_null(self) -> None:
        """Optional UUID set to None must be stored as DynamoDB NULL."""
        self.assertEqual(self.item["customer_id"], {"NULL": True})

    def test_present_uuid_serialized_as_s(self) -> None:
        """Optional UUID with a value must be stored as DynamoDB S."""
        self.assertEqual(self.item["waiter_id"], {"S": str(_WAITER_ID)})

    def test_aware_datetime_includes_timezone_in_iso(self) -> None:
        """Timezone-aware datetime must serialize to an ISO string with a UTC marker."""
        iso = self.item["created_at"]["S"]
        self.assertTrue(
            iso.endswith("+00:00") or iso.endswith("Z"),
            f"Expected UTC timezone marker in ISO string, got: {iso}",
        )

    def test_enum_serialized_as_value_string(self) -> None:
        """Enum must be stored as its string value."""
        self.assertEqual(self.item["status"], {"S": "Reserved"})

    def test_round_trip_preserves_none_uuid(self) -> None:
        """customer_id=None must round-trip back to None."""
        restored = Reservation.from_dynamodb_item(self.item)
        self.assertIsNone(restored.customer_id)

    def test_round_trip_preserves_aware_datetime(self) -> None:
        """Datetime must round-trip with UTC timezone info intact."""
        restored = Reservation.from_dynamodb_item(self.item)
        self.assertIsNotNone(restored.created_at.tzinfo)
        self.assertEqual(restored.created_at, _CREATED_AT)

    def test_round_trip_preserves_enum(self) -> None:
        """ReservationStatus must round-trip as the same enum member."""
        restored = Reservation.from_dynamodb_item(self.item)
        self.assertEqual(restored.status, ReservationStatus.RESERVED)

    def test_full_round_trip(self) -> None:
        """All fields together must survive a to/from DynamoDB round-trip."""
        restored = Reservation.from_dynamodb_item(self.item)
        self.assertEqual(restored, self.reservation)


class TestLoginAttemptsExcludeNone(unittest.TestCase):
    """Tests for LoginAttempts _exclude_none=True serialization behaviour."""

    def test_lockout_until_none_is_omitted_from_item(self) -> None:
        """lockout_until=None must not appear in the DynamoDB item."""
        item = LoginAttempts(email="a@b.com", failed_attempts=2).to_dynamodb_item()
        self.assertNotIn("lockout_until", item)

    def test_lockout_until_set_is_present_in_item(self) -> None:
        """lockout_until with a value must be stored as DynamoDB N."""
        item = LoginAttempts(
            email="a@b.com", failed_attempts=5, lockout_until=9_999_999_999
        ).to_dynamodb_item()
        self.assertIn("lockout_until", item)
        self.assertEqual(item["lockout_until"], {"N": "9999999999"})

    def test_round_trip_without_lockout(self) -> None:
        """A LoginAttempts without lockout_until must round-trip with lockout_until=None."""
        la = LoginAttempts(email="a@b.com", failed_attempts=3)
        item = la.to_dynamodb_item()
        restored = LoginAttempts.from_dynamodb_item(item)
        self.assertEqual(restored.email, la.email)
        self.assertEqual(restored.failed_attempts, la.failed_attempts)
        self.assertIsNone(restored.lockout_until)

    def test_round_trip_with_lockout(self) -> None:
        """A LoginAttempts with lockout_until set must round-trip correctly."""
        la = LoginAttempts(
            email="a@b.com", failed_attempts=5, lockout_until=9_999_999_999
        )
        restored = LoginAttempts.from_dynamodb_item(la.to_dynamodb_item())
        self.assertEqual(restored, la)

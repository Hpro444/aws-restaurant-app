"""Tests for Location domain model, including time string parsing and serialization."""

import unittest
from datetime import time
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.location import Location

_LOCATION_ID = uuid4()
_NAME = "Downtown"
_ADDRESS = "123 Main Street"
_DESCRIPTION = "Central city location"
_IMAGE_URL = "https://example.com/downtown.jpg"


class TestLocationTimeStringParsing(unittest.TestCase):
    """Tests for Location time field parsing from DynamoDB strings."""

    def test_parse_valid_iso_time_string_open_time(self) -> None:
        """Location must parse 'HH:MM' strings to time objects for open_time."""
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time="10:30",
            close_time=time(22, 0),
        )
        self.assertIsInstance(location.open_time, time)
        self.assertEqual(location.open_time.hour, 10)
        self.assertEqual(location.open_time.minute, 30)

    def test_parse_valid_iso_time_string_close_time(self) -> None:
        """Location must parse 'HH:MM' strings to time objects for close_time."""
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time=time(10, 0),
            close_time="23:45",
        )
        self.assertIsInstance(location.close_time, time)
        self.assertEqual(location.close_time.hour, 23)
        self.assertEqual(location.close_time.minute, 45)

    def test_parse_midnight_time_string(self) -> None:
        """Location must correctly parse '00:00' (midnight)."""
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time="00:00",
            close_time=time(23, 59),
        )
        self.assertEqual(location.open_time, time(0, 0))

    def test_parse_end_of_day_time_string(self) -> None:
        """Location must correctly parse '23:59'."""
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time=time(0, 0),
            close_time="23:59",
        )
        self.assertEqual(location.close_time, time(23, 59))

    def test_accept_time_object_directly(self) -> None:
        """Location must accept time objects without conversion."""
        open_t = time(10, 0)
        close_t = time(22, 0)
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time=open_t,
            close_time=close_t,
        )
        self.assertEqual(location.open_time, open_t)
        self.assertEqual(location.close_time, close_t)


class TestLocationRoundTrip(unittest.TestCase):
    """Tests for Location serialization and deserialization round-trips."""

    def setUp(self) -> None:
        """Create a Location with time objects for round-trip testing."""
        self.location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time=time(10, 0),
            close_time=time(22, 0),
        )

    def test_to_dynamodb_item_serializes_times(self) -> None:
        """Serializing a Location must convert time objects to strings."""
        item = self.location.to_dynamodb_item()
        # Times are serialized to ISO format strings in the JSON representation
        self.assertIn("open_time", item)
        self.assertIn("close_time", item)

    def test_round_trip_preserves_all_fields(self) -> None:
        """Serializing then deserializing a Location must preserve all fields."""
        item = self.location.to_dynamodb_item()
        restored = Location.from_dynamodb_item(item)
        self.assertEqual(restored.id, self.location.id)
        self.assertEqual(restored.name, self.location.name)
        self.assertEqual(restored.address, self.location.address)
        self.assertEqual(restored.description, self.location.description)
        self.assertEqual(restored.image_url, self.location.image_url)
        self.assertEqual(restored.open_time, self.location.open_time)
        self.assertEqual(restored.close_time, self.location.close_time)

    def test_round_trip_with_string_time_input(self) -> None:
        """Deserializing DynamoDB data with string times must parse them correctly."""
        # Simulate DynamoDB returning times as strings
        location_with_string_times = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time="10:00",
            close_time="22:00",
        )
        # Now serialize and deserialize
        item = location_with_string_times.to_dynamodb_item()
        restored = Location.from_dynamodb_item(item)
        # Both times should be correct time objects
        self.assertEqual(restored.open_time, time(10, 0))
        self.assertEqual(restored.close_time, time(22, 0))

    def test_equality_after_round_trip(self) -> None:
        """A Location should equal itself after a round-trip serialization cycle."""
        item = self.location.to_dynamodb_item()
        restored = Location.from_dynamodb_item(item)
        self.assertEqual(restored, self.location)


class TestLocationAllFields(unittest.TestCase):
    """Tests for Location domain model field coverage."""

    def test_location_has_all_required_fields(self) -> None:
        """Location must have all required fields: id, name, address, description, image_url, open_time, close_time."""
        location = Location(
            id=_LOCATION_ID,
            name=_NAME,
            address=_ADDRESS,
            description=_DESCRIPTION,
            image_url=_IMAGE_URL,
            open_time=time(10, 0),
            close_time=time(22, 0),
        )
        self.assertTrue(hasattr(location, "id"))
        self.assertTrue(hasattr(location, "name"))
        self.assertTrue(hasattr(location, "address"))
        self.assertTrue(hasattr(location, "description"))
        self.assertTrue(hasattr(location, "image_url"))
        self.assertTrue(hasattr(location, "open_time"))
        self.assertTrue(hasattr(location, "close_time"))

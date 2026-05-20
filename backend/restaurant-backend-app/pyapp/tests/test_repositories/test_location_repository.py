"""Integration tests for LocationRepository deserialization."""

import unittest
from datetime import time
from unittest.mock import Mock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.location import Location
    from repositories.location_repository import LocationRepository

_LOCATION_ID = uuid4()
_LOCATION_NAME = "Downtown"
_LOCATION_ADDRESS = "123 Main Street"
_LOCATION_DESCRIPTION = "Central city location"
_LOCATION_IMAGE_URL = "https://example.com/downtown.jpg"


def _mock_dynamodb_item(location: Location) -> dict:
    """Convert a Location domain object to a mock DynamoDB low-level item (as boto3 would return it)."""
    return location.to_dynamodb_item()


class TestLocationRepositoryScan(unittest.TestCase):
    """Integration tests for LocationRepository.scan() with real deserialization."""

    def setUp(self) -> None:
        """Create a repository and sample location."""
        self.repo = LocationRepository()
        self.mock_location = Location(
            id=_LOCATION_ID,
            name=_LOCATION_NAME,
            address=_LOCATION_ADDRESS,
            description=_LOCATION_DESCRIPTION,
            image_url=_LOCATION_IMAGE_URL,
            open_time=time(10, 0),
            close_time=time(22, 0),
        )

    def _build_repo(self) -> LocationRepository:
        repo = LocationRepository()
        repo._client = Mock()
        repo._resolve_table_name = Mock(return_value="test-locations")
        return repo

    def test_scan_deserializes_locations_with_time_objects(self) -> None:
        """Repository.scan() must correctly deserialize Location objects with time fields."""
        repo = self._build_repo()
        repo._client.scan.return_value = {
            "Items": [_mock_dynamodb_item(self.mock_location)],
            "Count": 1,
        }

        result = repo.scan()

        self.assertEqual(len(result), 1)
        location = result[0]
        self.assertEqual(location.id, self.mock_location.id)
        self.assertEqual(location.name, self.mock_location.name)
        self.assertEqual(location.address, self.mock_location.address)
        self.assertEqual(location.description, self.mock_location.description)
        self.assertEqual(location.image_url, self.mock_location.image_url)
        self.assertIsInstance(location.open_time, time)
        self.assertIsInstance(location.close_time, time)
        self.assertEqual(location.open_time, time(10, 0))
        self.assertEqual(location.close_time, time(22, 0))
        repo._client.scan.assert_called_once()

    def test_scan_returns_empty_list_when_no_items(self) -> None:
        """Repository.scan() must return an empty list when the table is empty."""
        repo = self._build_repo()
        repo._client.scan.return_value = {"Items": [], "Count": 0}

        result = repo.scan()

        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)
        repo._client.scan.assert_called_once()

    def test_scan_deserializes_multiple_locations(self) -> None:
        """Repository.scan() must deserialize multiple locations in order."""
        repo = self._build_repo()

        location_2 = Location(
            id=uuid4(),
            name="Airport",
            address="456 Terminal Boulevard",
            description="Airport location",
            image_url="https://example.com/airport.jpg",
            open_time=time(6, 0),
            close_time=time(23, 0),
        )

        repo._client.scan.return_value = {
            "Items": [
                _mock_dynamodb_item(self.mock_location),
                _mock_dynamodb_item(location_2),
            ],
            "Count": 2,
        }

        result = repo.scan()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, self.mock_location.name)
        self.assertEqual(result[1].name, location_2.name)
        repo._client.scan.assert_called_once()

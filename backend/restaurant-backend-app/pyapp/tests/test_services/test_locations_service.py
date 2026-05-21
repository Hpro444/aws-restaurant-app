"""Unit tests for LocationsService."""

from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from datetime import time

    from domain.location import Location
    from domain.table import Table
    from dto.locations import LocationNameResponse, LocationResponse
    from services.locations_service import LocationsService


class TestLocationsService(TestCase):
    """Unit tests that verify LocationsService correctly retrieves locations and maps them to response DTOs."""

    def setUp(self) -> None:
        """Create service with mocked repository and sample domain entities."""
        self.mock_location_repo = MagicMock()
        self.mock_table_repo = MagicMock()
        self.mock_feedback_cuisine_repo = MagicMock()
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = []
        self.service = LocationsService(
            location_repository=self.mock_location_repo,
            table_repository=self.mock_table_repo,
            feedback_cuisine_repository=self.mock_feedback_cuisine_repo,
        )
        self.location_1 = Location(
            id=uuid4(),
            name="Downtown",
            address="123 Main Street",
            description="Central city location near the main square.",
            image_url="https://images.example.com/locations/downtown.jpg",
            open_time=time(10, 0),
            close_time=time(22, 0),
        )
        self.location_2 = Location(
            id=uuid4(),
            name="Airport Terminal",
            address="456 Terminal Boulevard",
            description="Fast-service location inside the international terminal.",
            image_url="https://images.example.com/locations/airport.jpg",
            open_time=time(6, 0),
            close_time=time(23, 0),
        )
        self.table_1 = Table(
            id=uuid4(),
            table_number=1,
            capacity=4,
            location_id=self.location_1.id,
        )
        self.table_2 = Table(
            id=uuid4(),
            table_number=2,
            capacity=6,
            location_id=self.location_1.id,
        )

    def _mock_empty_tables_for_locations(self) -> None:
        self.mock_table_repo.find_by_location_id.return_value = []

    def test_get_locations_success_returns_list(self) -> None:
        """get_locations should return a list of LocationResponse objects."""
        self.mock_location_repo.scan.return_value = [self.location_1, self.location_2]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_get_locations_maps_id_field(self) -> None:
        """LocationResponse.id must match Location.id as a string."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].id, str(self.location_1.id))

    def test_get_locations_maps_address_field(self) -> None:
        """LocationResponse.address must match Location.address."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].address, self.location_1.address)

    def test_get_locations_maps_description_field(self) -> None:
        """LocationResponse.description must match Location.description."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].description, self.location_1.description)

    def test_get_locations_maps_image_url_field(self) -> None:
        """LocationResponse.image_url must match Location.image_url."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].image_url, self.location_1.image_url)

    def test_get_locations_calculates_total_capacity_from_tables(self) -> None:
        """LocationResponse.total_capacity must be computed as sum of table capacities."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self.mock_table_repo.find_by_location_id.return_value = [
            self.table_1,
            self.table_2,
        ]
        result = self.service.get_locations()
        self.assertEqual(result[0].total_capacity, "10")

    def test_get_locations_total_capacity_is_zero_when_no_tables(self) -> None:
        """LocationResponse.total_capacity must be '0' when a location has no tables."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self.mock_table_repo.find_by_location_id.return_value = []
        result = self.service.get_locations()
        self.assertEqual(result[0].total_capacity, "0")

    def test_get_locations_sets_hardcoded_average_occupancy(self) -> None:
        """LocationResponse.average_occupancy must be a placeholder between 25 and 100."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        occupancy = int(result[0].average_occupancy)
        self.assertGreaterEqual(occupancy, 25)
        self.assertLessEqual(occupancy, 100)

    def test_get_locations_average_occupancy_is_stable_per_location(self) -> None:
        """Placeholder average_occupancy must stay stable for the same location id."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        first = self.service.get_locations()[0].average_occupancy
        second = self.service.get_locations()[0].average_occupancy
        self.assertEqual(first, second)

    def test_get_locations_rating_is_zero_when_no_feedback(self) -> None:
        """LocationResponse.rating is '0' when there is no culinary feedback."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].rating, "0")

    def test_get_locations_returns_empty_list_when_no_locations(self) -> None:
        """get_locations should return an empty list when repository returns no locations."""
        self.mock_location_repo.scan.return_value = []
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_locations_preserves_order(self) -> None:
        """get_locations must preserve the order of locations returned by repository."""
        self.mock_location_repo.scan.return_value = [
            self.location_2,
            self.location_1,
        ]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        self.assertEqual(result[0].address, self.location_2.address)
        self.assertEqual(result[1].address, self.location_1.address)

    def test_get_locations_calls_repository_scan_once(self) -> None:
        """get_locations must call repository.scan() exactly once."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        self.service.get_locations()
        self.mock_location_repo.scan.assert_called_once()

    def test_get_locations_calls_table_lookup_per_location(self) -> None:
        """get_locations must call table lookup once per location."""
        self.mock_location_repo.scan.return_value = [self.location_1, self.location_2]
        self.mock_table_repo.find_by_location_id.return_value = []
        self.service.get_locations()
        self.assertEqual(self.mock_table_repo.find_by_location_id.call_count, 2)

    def test_response_objects_are_location_response_instances(self) -> None:
        """All items in returned list must be LocationResponse instances."""
        self.mock_location_repo.scan.return_value = [self.location_1, self.location_2]
        self._mock_empty_tables_for_locations()
        result = self.service.get_locations()
        for item in result:
            self.assertIsInstance(item, LocationResponse)

    def test_get_locations_rating_zero_if_no_culinary_feedback(self) -> None:
        """LocationResponse.rating is '0' if there is no culinary feedback for the location."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = []
        result = self.service.get_locations()
        self.assertEqual(result[0].rating, "0")

    def test_get_locations_rating_single_feedback(self) -> None:
        """LocationResponse.rating equals the single culinary feedback rating as a decimal string."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = [
            MagicMock(rate=4)
        ]
        result = self.service.get_locations()
        self.assertEqual(result[0].rating, "4.0")

    def test_get_locations_rating_multiple_feedbacks(self) -> None:
        """LocationResponse.rating is the average of all culinary feedback ratings, 1 decimal place."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = [
            MagicMock(rate=5),
            MagicMock(rate=3),
            MagicMock(rate=4),
        ]
        result = self.service.get_locations()
        self.assertEqual(result[0].rating, "4.0")

    def test_get_locations_rating_ignores_none_ratings(self) -> None:
        """LocationResponse.rating ignores feedbacks with rating=None."""
        self.mock_location_repo.scan.return_value = [self.location_1]
        self._mock_empty_tables_for_locations()
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = [
            MagicMock(rate=5),
            MagicMock(rate=None),
            MagicMock(rate=1),
        ]
        result = self.service.get_locations()
        self.assertEqual(result[0].rating, "3.0")

    def test_get_location_by_id_success(self) -> None:
        """get_location_by_id returns a LocationResponse when location exists."""
        self.mock_location_repo.get.return_value = self.location_1
        self.mock_table_repo.find_by_location_id.return_value = [
            self.table_1,
            self.table_2,
        ]
        self.mock_feedback_cuisine_repo.find_by_location_id.return_value = [
            MagicMock(rate=5),
            MagicMock(rate=3),
        ]

        result = self.service.get_location_by_id(self.location_1.id)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.id, str(self.location_1.id))
        self.assertEqual(result.total_capacity, "10")
        self.assertEqual(result.image_url, self.location_1.image_url)
        self.assertEqual(result.rating, "4.0")

    def test_get_location_by_id_returns_none_when_missing(self) -> None:
        """get_location_by_id returns None when repository has no location for id."""
        self.mock_location_repo.get.return_value = None

        result = self.service.get_location_by_id(uuid4())

        self.assertIsNone(result)

    def test_get_location_addresses_success_returns_list(self) -> None:
        """get_location_addresses should return a list of LocationNameResponse objects."""
        self.mock_location_repo.scan.return_value = [self.location_1, self.location_2]

        result = self.service.get_location_addresses()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], LocationNameResponse)
        self.assertIsInstance(result[1], LocationNameResponse)

    def test_get_location_addresses_maps_location_address_field(self) -> None:
        """LocationNameResponse.location_address must match Location.address."""
        self.mock_location_repo.scan.return_value = [self.location_1]

        result = self.service.get_location_addresses()

        self.assertEqual(result[0].location_address, self.location_1.address)

    def test_get_location_addresses_maps_location_id_field(self) -> None:
        """LocationNameResponse.location_id must match Location.id as string."""
        self.mock_location_repo.scan.return_value = [self.location_1]

        result = self.service.get_location_addresses()

        self.assertEqual(result[0].location_id, str(self.location_1.id))

    def test_get_location_addresses_returns_empty_list_when_no_locations(self) -> None:
        """get_location_addresses should return an empty list when repository returns no locations."""
        self.mock_location_repo.scan.return_value = []

        result = self.service.get_location_addresses()

        self.assertEqual(result, [])

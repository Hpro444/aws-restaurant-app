"""Tests for the GET /locations endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from dto.locations import LocationNameResponse, LocationResponse
from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase, body, status

_PATH = "/locations"
_NAMES_PATH = "/locations/select-options"


class TestLocationsEndpoint(ApiHandlerLambdaTestCase):
    """Tests for the public GET /locations endpoint."""

    def test_success_returns_200_with_locations_array(self) -> None:
        """GET /locations should return 200 with a raw array of LocationResponse objects."""
        location_id_1 = str(uuid4())
        location_id_2 = str(uuid4())
        mock_locations = [
            LocationResponse(
                id=location_id_1,
                address="123 Main Street",
                description="Downtown location",
                total_capacity="50",
                average_occupancy="75",
                image_url="https://example.com/downtown.jpg",
                rating="4.5",
            ),
            LocationResponse(
                id=location_id_2,
                address="456 Airport Boulevard",
                description="Airport location",
                total_capacity="40",
                average_occupancy="60",
                image_url="https://example.com/airport.jpg",
                rating="4.2",
            ),
        ]
        self.HANDLER._locations_service.get_locations = MagicMock(
            return_value=mock_locations
        )

        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        response_body = body(result)
        self.assertIsInstance(response_body, list)
        self.assertEqual(len(response_body), 2)
        self.assertEqual(response_body[0]["address"], "123 Main Street")
        self.assertEqual(response_body[1]["address"], "456 Airport Boulevard")
        self.HANDLER._locations_service.get_locations.assert_called_once()

    def test_success_returns_200_with_empty_array_when_no_locations(self) -> None:
        """GET /locations should return 200 with an empty array when no locations exist."""
        self.HANDLER._locations_service.get_locations = MagicMock(return_value=[])

        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])
        self.HANDLER._locations_service.get_locations.assert_called_once()

    def test_response_contains_all_required_fields(self) -> None:
        """Each location in the response must have all required fields."""
        location_id = str(uuid4())
        mock_location = LocationResponse(
            id=location_id,
            address="123 Main Street",
            description="Test location",
            total_capacity="50",
            average_occupancy="75",
            image_url="https://example.com/test.jpg",
            rating="4.5",
        )
        self.HANDLER._locations_service.get_locations = MagicMock(
            return_value=[mock_location]
        )

        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        location_response = body(result)[0]
        required_fields = [
            "id",
            "address",
            "description",
            "total_capacity",
            "average_occupancy",
            "image_url",
            "rating",
        ]
        for field in required_fields:
            self.assertIn(field, location_response)

    def test_wrong_method_returns_404(self) -> None:
        """A POST to /locations should return 404."""
        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "POST", "body": "{}"},
            {},
        )

        self.assertEqual(status(result), 404)

    def test_response_is_raw_array_not_wrapped(self) -> None:
        """Response must be a raw array, not wrapped in an object."""
        mock_locations = [
            LocationResponse(
                id=str(uuid4()),
                address="123 Main Street",
                description="Downtown",
                total_capacity="50",
                average_occupancy="75",
                image_url="https://example.com/test.jpg",
                rating="4.5",
            )
        ]
        self.HANDLER._locations_service.get_locations = MagicMock(
            return_value=mock_locations
        )

        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        response_body = body(result)
        self.assertIsInstance(response_body, list)
        self.assertNotIsInstance(response_body, dict)

    def test_get_location_by_id_success_returns_200_with_object(self) -> None:
        """GET /locations/{id} should return 200 with a single LocationResponse object."""
        location_id = str(uuid4())
        mock_location = LocationResponse(
            id=location_id,
            address="123 Main Street",
            description="Downtown location",
            total_capacity="50",
            average_occupancy="75",
            image_url="https://example.com/downtown.jpg",
            rating="4.5",
        )
        self.HANDLER._locations_service.get_location_by_id = MagicMock(
            return_value=mock_location
        )

        result = self.HANDLER.lambda_handler(
            {
                "path": f"/locations/{location_id}",
                "resource": "/locations/{id}",
                "pathParameters": {"id": location_id},
                "httpMethod": "GET",
            },
            {},
        )

        self.assertEqual(status(result), 200)
        response_body = body(result)
        self.assertIsInstance(response_body, dict)
        self.assertEqual(response_body["id"], location_id)
        self.assertEqual(response_body["address"], "123 Main Street")

    def test_get_location_by_id_invalid_uuid_returns_422(self) -> None:
        """GET /locations/{id} should return 422 when id is not a valid UUID."""
        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/not-a-uuid",
                "resource": "/locations/{id}",
                "pathParameters": {"id": "not-a-uuid"},
                "httpMethod": "GET",
            },
            {},
        )

        self.assertEqual(status(result), 422)

    def test_get_location_by_id_not_found_returns_404(self) -> None:
        """GET /locations/{id} should return 404 when location does not exist."""
        location_id = str(uuid4())
        self.HANDLER._locations_service.get_location_by_id = MagicMock(
            return_value=None
        )

        result = self.HANDLER.lambda_handler(
            {
                "path": f"/locations/{location_id}",
                "resource": "/locations/{id}",
                "pathParameters": {"id": location_id},
                "httpMethod": "GET",
            },
            {},
        )

        self.assertEqual(status(result), 404)

    def test_get_location_addresses_success_returns_200_with_address_array(
        self,
    ) -> None:
        """GET /locations/select-options should return 200 with location_id + location_address objects."""
        location_id_1 = str(uuid4())
        location_id_2 = str(uuid4())
        mock_names = [
            LocationNameResponse(
                location_id=location_id_1,
                location_address="123 Main Street",
            ),
            LocationNameResponse(
                location_id=location_id_2,
                location_address="456 Airport Boulevard",
            ),
        ]
        self.HANDLER._locations_service.get_location_addresses = MagicMock(
            return_value=mock_names
        )

        result = self.HANDLER.lambda_handler(
            {"path": _NAMES_PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        response_body = body(result)
        self.assertIsInstance(response_body, list)
        self.assertEqual(response_body[0]["location_id"], location_id_1)
        self.assertEqual(response_body[0]["location_address"], "123 Main Street")
        self.assertEqual(response_body[1]["location_id"], location_id_2)
        self.assertEqual(
            response_body[1]["location_address"],
            "456 Airport Boulevard",
        )
        self.HANDLER._locations_service.get_location_addresses.assert_called_once()

    def test_get_location_addresses_returns_200_with_empty_array(self) -> None:
        """GET /locations/select-options should return 200 with an empty array when no locations exist."""
        self.HANDLER._locations_service.get_location_addresses = MagicMock(
            return_value=[]
        )

        result = self.HANDLER.lambda_handler(
            {"path": _NAMES_PATH, "httpMethod": "GET"},
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])

    def test_get_location_addresses_wrong_method_returns_404(self) -> None:
        """A POST to /locations/names should return 404."""
        result = self.HANDLER.lambda_handler(
            {"path": _NAMES_PATH, "httpMethod": "POST", "body": "{}"},
            {},
        )

        self.assertEqual(status(result), 404)

"""Tests for the GET /locations/{id}/speciality-dishes endpoint."""

from unittest.mock import MagicMock
from uuid import UUID

from commons.exceptions import ApplicationException
from dto.dishes import DishResponse
from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase, body, status

_LOCATION_ID = "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3"
_PATH = f"/locations/{_LOCATION_ID}/speciality-dishes"

_STEAK_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


class TestSpecialityDishes(ApiHandlerLambdaTestCase):
    """Tests for the public speciality dishes endpoint by location."""

    def test_success_returns_200_with_speciality_dishes(self) -> None:
        """A valid location id should return a raw array with the expected fields."""
        dishes = [
            DishResponse(
                id=_STEAK_ID,
                name="Steak Special",
                description="Premium cut grilled to perfection.",
                image_url="https://example.com/steak.jpg",
                price=21.0,
                weight_gram=350,
                state="Available",
            )
        ]
        self.HANDLER._dishes_service.get_speciality_dishes_by_location = MagicMock(
            return_value=dishes
        )

        result = self.HANDLER.lambda_handler(
            {"path": _PATH, "httpMethod": "GET", "queryStringParameters": None},
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(
            body(result),
            [
                {
                    "id": str(_STEAK_ID),
                    "name": "Steak Special",
                    "description": "Premium cut grilled to perfection.",
                    "image_url": "https://example.com/steak.jpg",
                    "price": 21.0,
                    "weight_gram": 350,
                    "state": "Available",
                }
            ],
        )
        self.HANDLER._dishes_service.get_speciality_dishes_by_location.assert_called_once()

    def test_success_returns_200_with_empty_array_when_no_speciality_dishes(
        self,
    ) -> None:
        """If no speciality dishes exist for the location, return 200 with empty list."""
        self.HANDLER._dishes_service.get_speciality_dishes_by_location = MagicMock(
            return_value=[]
        )

        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/speciality-dishes",
                "httpMethod": "GET",
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])
        self.HANDLER._dishes_service.get_speciality_dishes_by_location.assert_called_once()

    def test_invalid_location_id_returns_422(self) -> None:
        """A malformed location id in the path should return 422."""
        self.HANDLER._dishes_service.get_speciality_dishes_by_location = MagicMock()

        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/not-a-uuid/speciality-dishes",
                "httpMethod": "GET",
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._dishes_service.get_speciality_dishes_by_location.assert_not_called()

    def test_unknown_location_id_returns_404(self) -> None:
        """A valid UUID that does not exist should return 404 with clear message."""
        self.HANDLER._dishes_service.get_speciality_dishes_by_location = MagicMock(
            side_effect=ApplicationException(code=404, content="Location not found")
        )

        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/speciality-dishes",
                "httpMethod": "GET",
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Location not found")
        self.HANDLER._dishes_service.get_speciality_dishes_by_location.assert_called_once()

    def test_path_parameters_id_is_used_when_present(self) -> None:
        """When API Gateway provides pathParameters.id, handler should use it."""
        self.HANDLER._dishes_service.get_speciality_dishes_by_location = MagicMock(
            return_value=[]
        )

        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/not-a-uuid/speciality-dishes",
                "httpMethod": "GET",
                "pathParameters": {"id": _LOCATION_ID},
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])
        self.HANDLER._dishes_service.get_speciality_dishes_by_location.assert_called_once()

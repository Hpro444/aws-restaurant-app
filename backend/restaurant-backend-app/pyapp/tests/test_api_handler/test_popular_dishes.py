"""Tests for the GET /dishes/popular endpoint."""

from unittest.mock import MagicMock

from dto.popular_dishes import DishResponse
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_get_event,
    status,
)

_PATH = "/dishes/popular"


class TestPopularDishes(ApiHandlerLambdaTestCase):
    """Tests for the public popular dishes endpoint."""

    def test_success_returns_200_with_popular_dishes(self) -> None:
        """A valid GET should return an array with only the expected dish fields."""
        dishes = [
            DishResponse(
                name="Margarita Pizza",
                image_url="https://example.com/pizza.jpg",
                price=12.5,
                weight_gram=480,
            ),
            DishResponse(
                name="Greek Salad",
                image_url="https://example.com/salad.jpg",
                price=8.0,
                weight_gram=260,
            ),
        ]
        self.HANDLER._dishes_service.get_popular_dishes = MagicMock(return_value=dishes)

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(
            body(result),
            [
                {
                    "name": "Margarita Pizza",
                    "image_url": "https://example.com/pizza.jpg",
                    "price": 12.5,
                    "weight_gram": 480,
                },
                {
                    "name": "Greek Salad",
                    "image_url": "https://example.com/salad.jpg",
                    "price": 8.0,
                    "weight_gram": 260,
                },
            ],
        )
        self.HANDLER._dishes_service.get_popular_dishes.assert_called_once_with()

    def test_success_returns_200_with_empty_array_when_no_popular_dishes(self) -> None:
        """When no popular dishes exist, endpoint should return 200 with an empty list."""
        self.HANDLER._dishes_service.get_popular_dishes = MagicMock(return_value=[])

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])
        self.HANDLER._dishes_service.get_popular_dishes.assert_called_once_with()

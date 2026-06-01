"""Tests for the GET /dishes/popular endpoint."""

from unittest.mock import MagicMock
from uuid import UUID

from dto.dishes import DishResponse
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_get_event,
    status,
)

_PATH = "/dishes/popular"

_PIZZA_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_SALAD_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


class TestPopularDishes(ApiHandlerLambdaTestCase):
    """Tests for the public popular dishes endpoint."""

    def test_success_returns_200_with_popular_dishes(self) -> None:
        """A valid GET should return an array with only the expected dish fields."""
        dishes = [
            DishResponse(
                id=_PIZZA_ID,
                name="Margarita Pizza",
                description="Classic pizza with tomato sauce.",
                image_url="https://example.com/pizza.jpg",
                price=12.5,
                weight_gram=480,
                state="Available",
            ),
            DishResponse(
                id=_SALAD_ID,
                name="Greek Salad",
                description="Fresh salad with feta cheese.",
                image_url="https://example.com/salad.jpg",
                price=8.0,
                weight_gram=260,
                state="Available",
            ),
        ]
        self.HANDLER._dishes_service.get_popular_dishes = MagicMock(return_value=dishes)

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(
            body(result),
            [
                {
                    "id": str(_PIZZA_ID),
                    "name": "Margarita Pizza",
                    "description": "Classic pizza with tomato sauce.",
                    "image_url": "https://example.com/pizza.jpg",
                    "price": 12.5,
                    "weight_gram": 480,
                    "state": "Available",
                },
                {
                    "id": str(_SALAD_ID),
                    "name": "Greek Salad",
                    "description": "Fresh salad with feta cheese.",
                    "image_url": "https://example.com/salad.jpg",
                    "price": 8.0,
                    "weight_gram": 260,
                    "state": "Available",
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

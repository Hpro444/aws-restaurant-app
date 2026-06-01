"""Tests for the GET /dishes endpoint."""

from unittest.mock import MagicMock
from uuid import UUID

from dto.dishes import DishResponse
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_get_event,
    status,
)

_PATH = "/dishes"

_PIZZA_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_SALAD_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

_PIZZA = DishResponse(
    id=_PIZZA_ID,
    name="Margherita Pizza",
    description="Classic pizza with tomato sauce, fresh mozzarella, and basil.",
    image_url="https://example.com/images/margherita.jpg",
    price=12.99,
    weight_gram=450,
    state="Available",
)
_SALAD = DishResponse(
    id=_SALAD_ID,
    name="Caesar Salad",
    description="Crispy romaine lettuce with Caesar dressing, croutons, and parmesan.",
    image_url="https://example.com/images/caesar.jpg",
    price=8.50,
    weight_gram=280,
    state="On stop",
)

_PIZZA_BODY = {
    "id": str(_PIZZA_ID),
    "name": "Margherita Pizza",
    "description": "Classic pizza with tomato sauce, fresh mozzarella, and basil.",
    "image_url": "https://example.com/images/margherita.jpg",
    "price": 12.99,
    "weight_gram": 450,
    "state": "Available",
}
_SALAD_BODY = {
    "id": str(_SALAD_ID),
    "name": "Caesar Salad",
    "description": "Crispy romaine lettuce with Caesar dressing, croutons, and parmesan.",
    "image_url": "https://example.com/images/caesar.jpg",
    "price": 8.50,
    "weight_gram": 280,
    "state": "On stop",
}


class TestGetDishes(ApiHandlerLambdaTestCase):
    """Tests for the public GET /dishes endpoint."""

    def test_success_returns_200_with_all_dishes_when_no_params(self) -> None:
        """No query params returns all dishes."""
        self.HANDLER._dishes_service.get_all_dishes = MagicMock(
            return_value=[_PIZZA, _SALAD]
        )

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [_PIZZA_BODY, _SALAD_BODY])
        self.HANDLER._dishes_service.get_all_dishes.assert_called_once_with(
            dish_type=None, sort=None
        )

    def test_success_returns_200_with_empty_array_when_no_dishes(self) -> None:
        """When no dishes match, endpoint returns 200 with empty list."""
        self.HANDLER._dishes_service.get_all_dishes = MagicMock(return_value=[])

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])

    def test_dishType_param_is_forwarded_to_service(self) -> None:
        """A valid dishType query param is parsed and passed to the service."""
        from enums.dish_type import DishType

        self.HANDLER._dishes_service.get_all_dishes = MagicMock(return_value=[_PIZZA])

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"dishType": "APPETIZER"}), {}
        )

        self.assertEqual(status(result), 200)
        self.HANDLER._dishes_service.get_all_dishes.assert_called_once_with(
            dish_type=DishType.APPETIZER, sort=None
        )

    def test_sort_param_is_forwarded_to_service(self) -> None:
        """A valid sort query param is parsed and passed to the service."""
        from dto.dishes import DishSort

        self.HANDLER._dishes_service.get_all_dishes = MagicMock(
            return_value=[_SALAD, _PIZZA]
        )

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"sort": "price,asc"}), {}
        )

        self.assertEqual(status(result), 200)
        self.HANDLER._dishes_service.get_all_dishes.assert_called_once_with(
            dish_type=None, sort=DishSort.PRICE_ASC
        )

    def test_invalid_sort_returns_422(self) -> None:
        """An unrecognised sort value returns 422."""
        self.HANDLER._dishes_service.get_all_dishes = MagicMock()

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"sort": "invalid"}), {}
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._dishes_service.get_all_dishes.assert_not_called()

    def test_invalid_dishType_returns_422(self) -> None:
        """An unrecognised dishType value returns 422."""
        self.HANDLER._dishes_service.get_all_dishes = MagicMock()

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"dishType": "INVALID_TYPE"}), {}
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._dishes_service.get_all_dishes.assert_not_called()

"""Tests for the GET /dishes/{id} endpoint."""

from unittest.mock import MagicMock
from uuid import UUID

from dto.dishes import DishExtendedResponse
from enums.dish_state import DishState
from enums.dish_type import DishType
from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase, body, status

_DISH_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_PATH = f"/dishes/{_DISH_ID}"


class TestDishById(ApiHandlerLambdaTestCase):
    """Tests for the public GET /dishes/{id} endpoint."""

    def test_success_returns_200_with_extended_dish(self) -> None:
        """A valid id should return a single extended dish object."""
        dish = DishExtendedResponse(
            id=_DISH_ID,
            name="Margherita Pizza",
            description="Classic pizza with tomato sauce, fresh mozzarella, and basil.",
            image_url="https://example.com/images/margherita.jpg",
            dish_type=DishType.MAIN_COURSE,
            price=12.99,
            state=DishState.AVAILABLE,
            calories="290 kcal",
            carbohydrates="32 g",
            fats="10 g",
            proteins="14 g",
            vitamins="A, C",
            weight_gram=450,
        )
        self.HANDLER._dishes_service.get_dish_by_id = MagicMock(return_value=dish)

        result = self.HANDLER.lambda_handler(make_event(), {})

        self.assertEqual(status(result), 200)
        self.assertEqual(
            body(result),
            {
                "id": str(_DISH_ID),
                "name": "Margherita Pizza",
                "description": "Classic pizza with tomato sauce, fresh mozzarella, and basil.",
                "image_url": "https://example.com/images/margherita.jpg",
                "dish_type": "MAIN_COURSE",
                "price": 12.99,
                "state": "Available",
                "calories": "290 kcal",
                "carbohydrates": "32 g",
                "fats": "10 g",
                "proteins": "14 g",
                "vitamins": "A, C",
                "weight_gram": 450,
            },
        )
        self.HANDLER._dishes_service.get_dish_by_id.assert_called_once_with(_DISH_ID)

    def test_invalid_dish_id_returns_422(self) -> None:
        """A malformed dish id should return 422."""
        self.HANDLER._dishes_service.get_dish_by_id = MagicMock()

        result = self.HANDLER.lambda_handler(
            {
                "path": "/dishes/not-a-uuid",
                "httpMethod": "GET",
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.assertEqual(
            body(result),
            {
                "errors": [
                    {
                        "field": "id",
                        "message": "'id' must be a valid UUID",
                    }
                ]
            },
        )
        self.HANDLER._dishes_service.get_dish_by_id.assert_not_called()

    def test_dish_not_found_returns_404(self) -> None:
        """An unknown dish id should return 404."""
        self.HANDLER._dishes_service.get_dish_by_id = MagicMock(return_value=None)

        result = self.HANDLER.lambda_handler(make_event(), {})

        self.assertEqual(status(result), 404)
        self.assertEqual(
            body(result),
            {
                "errors": [
                    {
                        "field": "id",
                        "message": "Dish not found",
                    }
                ]
            },
        )
        self.HANDLER._dishes_service.get_dish_by_id.assert_called_once_with(_DISH_ID)


def make_event() -> dict:
    """Build a minimal API Gateway-style GET event for dish-by-id."""
    return {
        "path": _PATH,
        "httpMethod": "GET",
        "queryStringParameters": None,
    }

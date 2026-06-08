"""Unit tests for DishesService."""

from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.dish import Dish
    from dto.dishes import DishDietaryFilter
    from enums.dish_state import DishState
    from enums.dish_type import DishType
    from services.dishes_service import DishesService


class TestDishesService(TestCase):
    """Unit tests that verify dish filtering and mapping behavior."""

    def setUp(self) -> None:
        """Create service with mocked repositories and sample dishes."""
        self.mock_dish_repo = MagicMock()
        self.mock_location_repo = MagicMock()
        self.service = DishesService(
            dish_repository=self.mock_dish_repo,
            location_repository=self.mock_location_repo,
        )

        location_id = uuid4()
        self.vegan_dish = Dish(
            id=uuid4(),
            location_id=location_id,
            name="Vegan Bowl",
            description="Fresh vegetables and quinoa. Dietary: vegan and gluten free.",
            image_url="https://example.com/vegan.jpg",
            price=12.0,
            weight_gram=350,
            specialty=False,
            popular=True,
            state=DishState.AVAILABLE,
            dish_type=DishType.APPETIZER,
        )
        self.classic_dish = Dish(
            id=uuid4(),
            location_id=location_id,
            name="Classic Pasta",
            description="Traditional pasta with cheese and butter.",
            image_url="https://example.com/pasta.jpg",
            price=15.0,
            weight_gram=400,
            specialty=False,
            popular=False,
            state=DishState.AVAILABLE,
            dish_type=DishType.MAIN_COURSE,
        )

    def test_get_all_dishes_filters_by_dietary_filter(self) -> None:
        """Only dishes containing the requested dietary tag are returned."""
        self.mock_dish_repo.scan.return_value = [self.vegan_dish, self.classic_dish]

        result = self.service.get_all_dishes(
            dietary_filter=DishDietaryFilter.VEGAN,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, self.vegan_dish.id)

    def test_get_all_dishes_gluten_free_matches_description_with_space(self) -> None:
        """GLUTEN_FREE filter should match description text written as 'gluten free'."""
        self.mock_dish_repo.scan.return_value = [self.vegan_dish, self.classic_dish]

        result = self.service.get_all_dishes(
            dietary_filter=DishDietaryFilter.GLUTEN_FREE,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, self.vegan_dish.id)

    def test_get_all_dishes_returns_empty_when_no_dietary_matches(self) -> None:
        """An empty list is returned when no dish matches the dietary filter."""
        self.mock_dish_repo.scan.return_value = [self.classic_dish]

        result = self.service.get_all_dishes(
            dietary_filter=DishDietaryFilter.DAIRY_FREE,
        )

        self.assertEqual(result, [])

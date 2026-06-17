"""Service for retrieving dishes from DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from domain.dish import Dish
from dto.dishes import (
    DishDietaryFilter,
    DishExtendedResponse,
    DishPreviewResponse,
    DishSort,
)
from enums.dish_type import DishType
from enums.http_status_code import HttpStatusCode
from repositories.dish_repository import DishRepository
from repositories.location_repository import LocationRepository


class DishesService:
    """Retrieve and transform dish data for API responses.

    Uses the DishRepository with GSI optimization to efficiently
    query popular and speciality dishes.
    """

    def __init__(
        self,
        settings: AppConfig | None = None,
        dish_repository: DishRepository | None = None,
        location_repository: LocationRepository | None = None,
    ) -> None:
        """Create repository for dish queries, creating defaults when omitted.

        Args:
            settings: Shared application config.
            dish_repository: Optional DishRepository instance.
            location_repository: Optional LocationRepository instance.

        """
        cfg = settings or AppConfig()
        self._dish_repo = dish_repository or DishRepository(cfg)
        self._location_repo = location_repository or LocationRepository(cfg)

    @staticmethod
    def _to_preview_response(dish: Dish) -> DishPreviewResponse:
        """Map a Dish domain object to preview response DTO."""
        return DishPreviewResponse(
            id=dish.id,
            name=dish.name,
            description=dish.description,
            image_url=dish.image_url,
            price=dish.price,
            weight_gram=dish.weight_gram,
            state=dish.state,
        )

    @staticmethod
    def _to_extended_response(dish: Dish) -> DishExtendedResponse:
        """Map a Dish domain object to extended response DTO."""
        return DishExtendedResponse(
            id=dish.id,
            name=dish.name,
            description=dish.description,
            image_url=dish.image_url,
            dish_type=dish.dish_type,
            price=dish.price,
            state=dish.state,
            calories=dish.calories,
            carbohydrates=dish.carbohydrates,
            fats=dish.fats,
            proteins=dish.proteins,
            vitamins=dish.vitamins,
            weight_gram=dish.weight_gram,
        )

    def get_popular_dishes(self) -> list[DishPreviewResponse]:
        """Retrieve all popular dishes across all locations.

        Queries the ``popular_index`` GSI to efficiently find all dishes
        where popular=true, then transforms them into response DTOs.

        The GSI lookup is O(1) — no table scan required.
        Results include all locations; no filtering by location_id.

        Returns:
            List of popular DishPreviewResponse objects, or empty list if none exist.

        """
        logger.info("Retrieving popular dishes")

        # Query using GSI on popular flag (O(1) lookup)
        popular_dishes = self._dish_repo.find_by_popular()

        # Transform domain objects to response DTOs
        response = [self._to_preview_response(dish) for dish in popular_dishes]

        logger.info("Popular dishes retrieved", count=len(response))
        return response

    def get_speciality_dishes_by_location(
        self, location_id: UUID
    ) -> list[DishPreviewResponse]:
        """Retrieve all speciality dishes for a specific location.

        Queries the ``location_id_index`` GSI to find all dishes at the location,
        then filters locally on specialty=true. Uses GSI for scale; does not
        perform a table scan.

        Args:
            location_id: UUID of the restaurant location.

        Returns:
            List of speciality DishPreviewResponse objects for the location,
            or empty list if none exist.

        """
        logger.info(
            "Retrieving specialty dishes for location", location_id=str(location_id)
        )

        if not self._location_repo.get(location_id):
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Location not found",
            )

        # Query using GSI on location_id and filter on specialty locally
        specialty_dishes = self._dish_repo.find_by_location_and_specialty(
            str(location_id)
        )

        # Transform domain objects to response DTOs
        response = [self._to_preview_response(dish) for dish in specialty_dishes]

        logger.info(
            "Specialty dishes retrieved",
            location_id=str(location_id),
            count=len(response),
        )
        return response

    def get_all_dishes(
        self,
        dish_type: DishType | None = None,
        sort: DishSort | None = None,
        dietary_filter: DishDietaryFilter | None = None,
    ) -> list[DishPreviewResponse]:
        """Retrieve dishes filtered by type and sorted by the requested criterion.

        Performs a full table scan then applies in-memory filtering and sorting,
        which is acceptable for a small restaurant menu dataset.

        Args:
            dish_type: When provided, only dishes matching this category are returned.
            sort: Ordering applied after filtering. Supports price and popularity
                in ascending or descending direction.
            dietary_filter: When provided, only dishes matching this dietary filter
                are returned.

        Returns:
            List of DishPreviewResponse objects, or empty list when no dishes match.

        """
        logger.info(
            "Retrieving dishes",
            dish_type=dish_type and dish_type.value,
            sort=sort and sort.value,
            dietary_filter=dietary_filter and dietary_filter.value,
        )

        dishes = self._dish_repo.scan()

        if dish_type is not None:
            dishes = [d for d in dishes if d.dish_type == dish_type]

        if sort is not None:
            field, direction = sort.value.split(",")
            reverse = direction == "desc"
            if field == "price":
                dishes = sorted(dishes, key=lambda d: d.price, reverse=reverse)
            elif field == "popularity":
                dishes = sorted(dishes, key=lambda d: d.popular, reverse=reverse)

        if dietary_filter is not None:
            filter_token = dietary_filter.value.replace("_", " ")
            dishes = [
                dish
                for dish in dishes
                if filter_token in dish.description.upper().replace("_", " ")
            ]

        response = [self._to_preview_response(dish) for dish in dishes]

        logger.info("Dishes retrieved", count=len(response))
        return response

    def get_dish_by_id(self, dish_id: UUID) -> DishExtendedResponse | None:
        """Retrieve a single dish by id.

        Args:
            dish_id: UUID of the dish.

        Returns:
            DishExtendedResponse when found, otherwise None.

        """
        logger.info("Retrieving dish by id", dish_id=str(dish_id))
        dish = self._dish_repo.get(dish_id)
        if dish is None:
            logger.info("Dish not found", dish_id=str(dish_id))
            return None
        return self._to_extended_response(dish)

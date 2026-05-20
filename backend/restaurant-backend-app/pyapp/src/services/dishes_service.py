"""Service for retrieving popular and speciality dishes from DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from dto.popular_dishes import DishResponse
from repositories.dish_repository import DishRepository


class DishesService:
    """Retrieve and transform dish data for API responses.

    Uses the DishRepository with GSI optimization to efficiently
    query popular and speciality dishes.
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Create repository for dish queries.

        Args:
            settings: Shared application config.

        """
        cfg = settings or AppConfig()
        self._dish_repo = DishRepository(cfg)

    def get_popular_dishes(self) -> list[DishResponse]:
        """Retrieve all popular dishes across all locations.

        Queries the ``popular_index`` GSI to efficiently find all dishes
        where popular=true, then transforms them into response DTOs.

        The GSI lookup is O(1) — no table scan required.
        Results include all locations; no filtering by location_id.

        Returns:
            List of popular DishResponse objects, or empty list if none exist.

        """
        logger.info("Retrieving popular dishes")

        # Query using GSI on popular flag (O(1) lookup)
        popular_dishes = self._dish_repo.find_by_popular()

        # Transform domain objects to response DTOs
        response = [
            DishResponse(
                name=dish.name,
                image_url=dish.image_url,
                price=dish.price,
                weight_gram=dish.weight_gram,
            )
            for dish in popular_dishes
        ]

        logger.info("Popular dishes retrieved", count=len(response))
        return response

    def get_speciality_dishes_by_location(
        self, location_id: UUID
    ) -> list[DishResponse]:
        """Retrieve all speciality dishes for a specific location.

        Queries the ``location_id_index`` GSI to find all dishes at the location,
        then filters locally on specialty=true. Uses GSI for scale; does not
        perform a table scan.

        Args:
            location_id: UUID of the restaurant location.

        Returns:
            List of speciality DishResponse objects for the location,
            or empty list if none exist.

        """
        logger.info(
            "Retrieving specialty dishes for location", location_id=str(location_id)
        )

        # Query using GSI on location_id and filter on specialty locally
        specialty_dishes = self._dish_repo.find_by_location_and_specialty(
            str(location_id)
        )

        # Transform domain objects to response DTOs
        response = [
            DishResponse(
                name=dish.name,
                image_url=dish.image_url,
                price=dish.price,
                weight_gram=dish.weight_gram,
            )
            for dish in specialty_dishes
        ]

        logger.info(
            "Specialty dishes retrieved",
            location_id=str(location_id),
            count=len(response),
        )
        return response

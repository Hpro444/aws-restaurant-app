"""Repository for Dish entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.dish import Dish

from repositories.base_repository import DynamoRepository


class DishRepository(DynamoRepository[Dish]):
    """CRUD repository for Dish entities with popularity and speciality-based queries."""

    _POPULAR_INDEX = "popular_index"
    _POPULAR_INDEX_KEY = "popular"
    _LOCATION_ID_INDEX = "location_id_index"
    _LOCATION_ID_KEY = "location_id"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the dishes table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.dishes_table, Dish, cfg)

    def find_by_popular(self) -> list[Dish]:
        """Query all popular dishes using a GSI.

        Uses the ``popular_index`` Global Secondary Index to efficiently
        retrieve only dishes where popular=true.

        The indexed key attribute is ``popular`` stored as numeric 1/0,
        because DynamoDB index keys do not support BOOL values.
        No table scan; O(1) lookup for the popular partition.

        Returns:
            List of Dish domain objects where popular=true.

        """
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "popular_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._POPULAR_INDEX,
            KeyConditionExpression=f"{self._POPULAR_INDEX_KEY} = :popular",
            ExpressionAttributeValues={
                ":popular": {"N": "1"},
            },
        )

        logger.info(
            "Popular dishes queried",
            count=len(items),
        )
        return items

    def find_by_location_and_specialty(self, location_id: str) -> list[Dish]:
        """Query all speciality dishes for a specific location using a GSI.

        Uses the ``location_id_index`` Global Secondary Index to efficiently
        retrieve only dishes for the given location, then filters locally on
        specialty=true. This is O(n) where n is the number of dishes per location
        (typically small), with GSI ensuring we don't scan the full table.

        Args:
            location_id: UUID of the location to filter by.

        Returns:
            List of Dish domain objects where location_id matches and specialty=true.

        """
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "location_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._LOCATION_ID_INDEX,
            KeyConditionExpression=f"{self._LOCATION_ID_KEY} = :location_id",
            ExpressionAttributeValues={
                ":location_id": {"S": str(location_id)},
            },
        )

        # Filter in-memory for specialty=true
        specialty_dishes = [dish for dish in items if dish.specialty]

        logger.info(
            "Specialty dishes queried",
            location_id=str(location_id),
            count=len(specialty_dishes),
        )
        return specialty_dishes

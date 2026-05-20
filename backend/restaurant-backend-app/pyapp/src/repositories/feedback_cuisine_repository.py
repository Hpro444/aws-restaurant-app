"""Repository for FeedbackCuisine entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.feedback import FeedbackCuisine

from repositories.base_repository import DynamoRepository


class FeedbackCuisineRepository(DynamoRepository[FeedbackCuisine]):
    """CRUD repository for FeedbackCuisine entities."""

    _LOCATION_ID_KEY = "location_id"
    _LOCATION_ID_INDEX = "location_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the feedback-cuisine table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.feedback_cuisine_table, FeedbackCuisine, cfg)

    def find_by_location_id(self, location_id: UUID) -> list[FeedbackCuisine]:
        """Return all cuisine feedback entries for a given location.

        Args:
            location_id: The location UUID to filter by.

        Returns:
            List of FeedbackCuisine instances for that location.

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
        logger.info(
            "Cuisine feedback queried by location",
            location_id=str(location_id),
            count=len(items),
        )
        return items

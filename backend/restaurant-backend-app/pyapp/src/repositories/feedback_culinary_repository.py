"""Repository for FeedbackCulinary entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.feedback import FeedbackCulinary

from repositories.base_repository import DynamoRepository


class FeedbackCulinaryRepository(DynamoRepository[FeedbackCulinary]):
    """CRUD repository for FeedbackCulinary entities."""

    _LOCATION_ID_KEY = "location_id"
    _LOCATION_ID_INDEX = "location_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the feedback-culinary table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.feedback_culinary_table, FeedbackCulinary, cfg)

    def find_by_location_id(self, location_id: UUID) -> list[FeedbackCulinary]:
        """Return all culinary feedback entries for a given location.

        Args:
            location_id: The location UUID to filter by.

        Returns:
            List of FeedbackCulinary instances for that location.

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
            "Culinary feedback queried by location",
            location_id=str(location_id),
            count=len(items),
        )
        return items

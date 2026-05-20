"""Repository for Waiter entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.user import Waiter

from repositories.base_repository import DynamoRepository


class WaiterRepository(DynamoRepository[Waiter]):
    """CRUD repository for Waiter entities."""

    _LOCATION_INDEX = "location_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the waiters table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.waiters_table, Waiter, cfg)

    def find_by_location_id(self, location_id: UUID) -> list[Waiter]:
        """Query waiters belonging to a specific location using a GSI."""
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "location_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._LOCATION_INDEX,
            KeyConditionExpression="location_id = :lid",
            ExpressionAttributeValues={":lid": {"S": str(location_id)}},
        )

        logger.info(
            "Waiters queried by location",
            location_id=str(location_id),
            count=len(items),
        )
        return items

"""Repository for Table (restaurant table) entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.table import Table

from repositories.base_repository import DynamoRepository


class TableRepository(DynamoRepository[Table]):
    """CRUD repository for Table entities with location-based queries."""

    _LOCATION_INDEX = "location_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the tables table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.tables_table, Table, cfg)

    def find_by_location_id(self, location_id: UUID) -> list[Table]:
        """Query tables belonging to a specific location using a GSI.

        Uses the ``location_id_index`` Global Secondary Index to read
        only the partition that matches *location_id*. No table scan.

        Args:
            location_id: The location UUID to query by.

        Returns:
            List of Table domain objects at that location.

        """
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "location_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._LOCATION_INDEX,
            KeyConditionExpression="location_id = :lid",
            ExpressionAttributeValues={
                ":lid": {"S": str(location_id)},
            },
        )

        logger.info(
            "Tables queried by location",
            location_id=str(location_id),
            count=len(items),
        )
        return items

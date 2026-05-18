"""Repository for Slot entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.slot import Slot

from repositories.base_repository import DynamoRepository


class SlotRepository(DynamoRepository[Slot]):
    """CRUD repository for Slot entities with table+date queries."""

    _TABLE_DATE_INDEX = "table_id_date_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the slots table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.slots_table, Slot, cfg)

    def find_by_table_id_and_date(self, table_id: UUID, date_iso: str) -> list[Slot]:
        """Query slots for a specific table on a specific date using a GSI.

        Uses the ``table_id_date_index`` GSI where:
        - Partition key = ``table_id``
        - Sort key = ``date`` (AwareDatetime stored as ISO string)

        The sort key condition uses ``begins_with`` so that
        "2025-08-02" matches "2025-08-02T00:00:00+00:00".

        Args:
            table_id: UUID of the table.
            date_iso: Date as "YYYY-MM-DD" string.

        Returns:
            List of Slot domain objects for that table on that date.

        """
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "table_id_date_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._TABLE_DATE_INDEX,
            KeyConditionExpression=(
                "table_id = :tid AND begins_with(#d, :date_prefix)"
            ),
            ExpressionAttributeNames={
                "#d": "date",  # 'date' is a DynamoDB reserved word
            },
            ExpressionAttributeValues={
                ":tid": {"S": str(table_id)},
                ":date_prefix": {"S": date_iso},
            },
        )

        logger.info(
            "Slots queried by table and date",
            table_id=str(table_id),
            date=date_iso,
            count=len(items),
        )
        return items

    def find_by_table_ids_and_date(
        self, table_ids: set[UUID], date_iso: str
    ) -> list[Slot]:
        """Query slots for multiple tables on a specific date.

        Executes one GSI query per table_id and combines the results.
        Typically 3–5 queries, each returning 5–10 items.

        Args:
            table_ids: Set of table UUIDs.
            date_iso: Date as "YYYY-MM-DD" string.

        Returns:
            Combined list of Slot domain objects across all tables.

        """
        all_slots: list[Slot] = []
        for tid in table_ids:
            all_slots.extend(self.find_by_table_id_and_date(tid, date_iso))

        logger.info(
            "Slots queried for all tables",
            table_count=len(table_ids),
            date=date_iso,
            total_slots=len(all_slots),
        )
        return all_slots

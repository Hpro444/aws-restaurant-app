"""Repository for Slot entities in DynamoDB."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.slot import Slot
from enums import SlotStatus

from repositories.base_repository import DynamoRepository


class SlotRepository(DynamoRepository[Slot]):
    """CRUD repository for Slot entities with table+date queries."""

    _TABLE_DATE_INDEX = "table_id_date_index"
    _WAITER_DATE_INDEX = "waiter_id_date_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the slots table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.slots_table, Slot, cfg)

    def find_by_table_id_and_date(self, table_id: UUID, query_date: date) -> list[Slot]:
        """Query slots for a specific table on a specific date using a GSI.

        Uses the ``table_id_date_index`` GSI where:
        - Partition key = ``table_id``
        - Sort key = ``date`` (AwareDatetime stored as ISO string)

        The sort key condition uses ``begins_with`` so that the
        ``"2025-08-02"`` prefix matches ``"2025-08-02T00:00:00+00:00"``.

        Args:
            table_id: UUID of the table.
            query_date: Day to query for.

        Returns:
            List of Slot domain objects for that table on that date.

        """
        date_prefix = query_date.isoformat()
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
                ":date_prefix": {"S": date_prefix},
            },
        )

        logger.info(
            "Slots queried by table and date",
            table_id=str(table_id),
            date=date_prefix,
            count=len(items),
        )
        return items

    def find_by_table_ids_and_date(
        self, table_ids: set[UUID], query_date: date
    ) -> list[Slot]:
        """Query slots for multiple tables on a specific date.

        Executes one GSI query per table_id and combines the results.
        Typically 3–5 queries, each returning 5–10 items.

        Args:
            table_ids: Set of table UUIDs.
            query_date: Day to query for.

        Returns:
            Combined list of Slot domain objects across all tables.

        """
        all_slots: list[Slot] = []
        for tid in table_ids:
            all_slots.extend(self.find_by_table_id_and_date(tid, query_date))

        logger.info(
            "Slots queried for all tables",
            table_count=len(table_ids),
            date=query_date.isoformat(),
            total_slots=len(all_slots),
        )
        return all_slots

    def find_by_waiter_id_and_period(
        self,
        waiter_id: UUID,
        period_start: date,
        period_end: date,
    ) -> list[Slot]:
        """Query slots assigned to a waiter within a date range using a GSI.

        Uses the ``waiter_id_date_index`` GSI where:
        - Partition key = ``waiter_id``
        - Sort key = ``date`` (AwareDatetime stored as ISO string)

        Both ``period_start`` and ``period_end`` represent midnight UTC dates,
        so the BETWEEN bounds are fully inclusive.

        Args:
            waiter_id: UUID of the waiter.
            period_start: First day of the period (inclusive).
            period_end: Last day of the period (inclusive).

        Returns:
            List of Slot domain objects assigned to the waiter in the period.

        """
        table_name = self._resolve_table_name()
        start_str = f"{period_start.isoformat()}T00:00:00+00:00"
        end_str = f"{period_end.isoformat()}T00:00:00+00:00"
        items = self._paginated_query(
            "waiter_id_date_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._WAITER_DATE_INDEX,
            KeyConditionExpression="waiter_id = :wid AND #d BETWEEN :start AND :end",
            ExpressionAttributeNames={"#d": "date"},
            ExpressionAttributeValues={
                ":wid": {"S": str(waiter_id)},
                ":start": {"S": start_str},
                ":end": {"S": end_str},
            },
        )
        logger.info(
            "Slots queried by waiter and period",
            waiter_id=str(waiter_id),
            period_start=str(period_start),
            period_end=str(period_end),
            count=len(items),
        )
        return items

    def find_by_ids(self, slot_ids: list[UUID], consistent: bool = False) -> list[Slot]:
        """Return existing slots for the provided IDs in input order.

        Uses ``BatchGetItem`` to avoid one round-trip per slot id.

        Args:
            slot_ids: Slot IDs to fetch.
            consistent: When True, reads the base table with strong
                consistency — used by availability to confirm a slot is
                really FREE, since the GSI it lists from is only eventually
                consistent.

        """
        if not slot_ids:
            return []

        table_name = self._resolve_table_name()
        unique_ids = list(dict.fromkeys(slot_ids))

        found_by_id: dict[UUID, Slot] = {}
        for start in range(0, len(unique_ids), 100):
            chunk = unique_ids[start : start + 100]
            request_items = {
                table_name: {
                    "Keys": [
                        {self._pk_field: {"S": str(slot_id)}} for slot_id in chunk
                    ],
                    "ConsistentRead": consistent,
                }
            }

            while request_items:
                response = self._client.batch_get_item(RequestItems=request_items)
                raw_items = response.get("Responses", {}).get(table_name, [])
                for raw in raw_items:
                    slot = self._model_class.from_dynamodb_item(raw)
                    found_by_id[slot.id] = slot

                unprocessed = response.get("UnprocessedKeys", {})
                request_items = (
                    {table_name: unprocessed[table_name]}
                    if table_name in unprocessed
                    else {}
                )

        logger.info(
            "Slots fetched by ids",
            requested_count=len(slot_ids),
            found_count=len(found_by_id),
        )
        return [found_by_id[slot_id] for slot_id in slot_ids if slot_id in found_by_id]

    def update_status(
        self,
        slot_id: UUID,
        new_status: SlotStatus,
        expected: SlotStatus,
    ) -> bool:
        """Atomically transition a slot's status from ``expected`` to ``new_status``.

        Uses a DynamoDB ``ConditionExpression`` so two concurrent bookings
        cannot both claim the same slot — only the one whose pre-image
        matches ``expected`` succeeds.

        Args:
            slot_id: UUID of the slot to update.
            new_status: Target status to set.
            expected: Status the slot must currently hold for the update
                to proceed; mismatches return False.

        Returns:
            True on successful update; False if the conditional check
            failed (slot missing or in an unexpected state) or DynamoDB
            errored.

        """
        try:
            self._client.update_item(
                TableName=self._resolve_table_name(),
                Key={self._pk_field: {"S": str(slot_id)}},
                UpdateExpression="SET #s = :new",
                ConditionExpression="#s = :expected",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":new": {"S": new_status},
                    ":expected": {"S": expected},
                },
            )
            logger.info(
                "Slot status updated",
                slot_id=str(slot_id),
                new_status=new_status,
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info(
                    "Slot status update rejected by condition",
                    slot_id=str(slot_id),
                    expected=expected,
                )
                return False
            logger.error(
                "DynamoDB update_item (slot status) failed",
                slot_id=str(slot_id),
                error=str(exc),
            )
            return False

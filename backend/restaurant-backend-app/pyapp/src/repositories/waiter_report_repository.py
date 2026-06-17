"""Repository for WaiterReport entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.waiter_report import WaiterReport

from repositories.base_repository import DynamoRepository


class WaiterReportRepository(DynamoRepository[WaiterReport]):
    """CRUD repository for WaiterReport entities.

    The primary key ``id`` is used for direct lookups and upserts. The
    ``waiter_period_index`` GSI (PK=``waiter_id``, SK=``report_period_start``)
    supports fetching the row for a specific waiter + period and is also used to
    retrieve the previous period's row for delta calculations.
    """

    _WAITER_PERIOD_INDEX = "waiter_period_index"
    _REPORT_PERIOD_START_INDEX = "report_period_start_index"
    _REPORT_PERIOD_START_INDEX = "report_period_start_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the waiter-report table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.waiter_report_table, WaiterReport, cfg)

    def find_by_waiter_and_period(
        self,
        waiter_id: UUID,
        period_start: str,
    ) -> WaiterReport | None:
        """Return the report row for (waiter_id, period_start) or None.

        Args:
            waiter_id: UUID of the waiter.
            period_start: ISO date string ``"YYYY-MM-DD"`` for the period's Monday.

        """
        results = self._paginated_query(
            "waiter_period_index query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._WAITER_PERIOD_INDEX,
            KeyConditionExpression="waiter_id = :wid AND report_period_start = :ps",
            ExpressionAttributeValues={
                ":wid": {"S": str(waiter_id)},
                ":ps": {"S": period_start},
            },
            Limit=1,
        )
        logger.info(
            "WaiterReport GSI lookup",
            waiter_id=str(waiter_id),
            period_start=period_start,
            found=bool(results),
        )
        return results[0] if results else None

    def find_by_period_start(self, period_start: str) -> list[WaiterReport]:
        """Return all waiter report rows for a given ISO week start date.

        Args:
            period_start: ISO date string ``"YYYY-MM-DD"`` for the period's Monday.

        """
        results = self._paginated_query(
            "report_period_start_index query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._REPORT_PERIOD_START_INDEX,
            KeyConditionExpression="report_period_start = :ps",
            ExpressionAttributeValues={":ps": {"S": period_start}},
        )
        logger.info(
            "WaiterReport period lookup",
            period_start=period_start,
            count=len(results),
        )
        return results

    def find_latest_by_waiter_id(self, waiter_id: UUID) -> WaiterReport | None:
        """Return the most recent report row for waiter_id or None.

        Args:
            waiter_id: UUID of the waiter.

        """
        results = self._paginated_query(
            "waiter_period_index latest query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._WAITER_PERIOD_INDEX,
            KeyConditionExpression="waiter_id = :wid",
            ExpressionAttributeValues={
                ":wid": {"S": str(waiter_id)},
            },
            ScanIndexForward=False,
            Limit=1,
        )
        logger.info(
            "WaiterReport latest GSI lookup",
            waiter_id=str(waiter_id),
            found=bool(results),
        )
        return results[0] if results else None

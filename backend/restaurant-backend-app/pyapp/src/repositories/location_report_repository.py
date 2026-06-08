"""Repository for LocationReport entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.location_report import LocationReport

from repositories.base_repository import DynamoRepository


class LocationReportRepository(DynamoRepository[LocationReport]):
    """CRUD repository for LocationReport entities.

    The primary key ``id`` is used for direct lookups and upserts. The
    ``location_period_index`` GSI (PK=``location_id``, SK=``report_period_start``)
    supports fetching the row for a specific location + period and is also used to
    retrieve the previous period's row for delta calculations.
    """

    _LOCATION_PERIOD_INDEX = "location_period_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the location-report table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.location_report_table, LocationReport, cfg)

    def find_by_location_and_period(
        self,
        location_id: UUID,
        period_start: str,
    ) -> LocationReport | None:
        """Return the report row for (location_id, period_start) or None.

        Args:
            location_id: UUID of the location.
            period_start: ISO date string ``"YYYY-MM-DD"`` for the period's Monday.

        """
        results = self._paginated_query(
            "location_period_index query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._LOCATION_PERIOD_INDEX,
            KeyConditionExpression="location_id = :lid AND report_period_start = :ps",
            ExpressionAttributeValues={
                ":lid": {"S": str(location_id)},
                ":ps": {"S": period_start},
            },
            Limit=1,
        )
        logger.info(
            "LocationReport GSI lookup",
            location_id=str(location_id),
            period_start=period_start,
            found=bool(results),
        )
        return results[0] if results else None

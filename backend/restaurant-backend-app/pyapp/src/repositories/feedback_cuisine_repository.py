"""Repository for FeedbackCuisine entities in DynamoDB."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.feedback import FeedbackCuisine

from repositories.base_repository import DynamoRepository


class FeedbackCuisineRepository(DynamoRepository[FeedbackCuisine]):
    """CRUD repository for FeedbackCuisine entities."""

    _LOCATION_ID_KEY = "location_id"
    _LOCATION_ID_INDEX = "location_id_index"
    _LOCATION_DATE_INDEX = "location_id_date_index"

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

    def find_by_reservation_id(self, reservation_id: UUID) -> list[FeedbackCuisine]:
        """Return all cuisine feedback entries for a given reservation.

        Args:
            reservation_id: The reservation UUID to filter by.

        Returns:
            List of FeedbackCuisine instances for that reservation.

        """
        table_name = self._resolve_table_name()
        items = self._paginated_query(
            "reservation_id scan",
            self._client.scan,
            TableName=table_name,
            FilterExpression="reservation_id = :reservation_id",
            ExpressionAttributeValues={
                ":reservation_id": {"S": str(reservation_id)},
            },
        )
        logger.info(
            "Cuisine feedback scanned by reservation",
            reservation_id=str(reservation_id),
            count=len(items),
        )
        return items

    def find_by_location_id_and_period(
        self,
        location_id: UUID,
        period_start: date,
        period_end: date,
    ) -> list[FeedbackCuisine]:
        """Return cuisine feedback for a location within a date range using a GSI.

        Uses the ``location_id_date_index`` GSI where:
        - Partition key = ``location_id``
        - Sort key = ``date`` (AwareDatetime stored as ISO string)

        Args:
            location_id: UUID of the location.
            period_start: First day of the period (inclusive).
            period_end: Last day of the period (inclusive).

        Returns:
            List of FeedbackCuisine instances within the period.

        """
        table_name = self._resolve_table_name()
        start_str = f"{period_start.isoformat()}T00:00:00+00:00"
        end_str = f"{period_end.isoformat()}T23:59:59+00:00"
        items = self._paginated_query(
            "location_id_date_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._LOCATION_DATE_INDEX,
            KeyConditionExpression="location_id = :lid AND #d BETWEEN :start AND :end",
            ExpressionAttributeNames={"#d": "date"},
            ExpressionAttributeValues={
                ":lid": {"S": str(location_id)},
                ":start": {"S": start_str},
                ":end": {"S": end_str},
            },
        )
        logger.info(
            "Cuisine feedback queried by location and period",
            location_id=str(location_id),
            period_start=str(period_start),
            period_end=str(period_end),
            count=len(items),
        )
        return items

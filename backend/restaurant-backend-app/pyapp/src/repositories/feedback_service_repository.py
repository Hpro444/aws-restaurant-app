"""Repository for FeedbackService entities in DynamoDB."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.feedback import FeedbackService

from repositories.base_repository import DynamoRepository
from repositories.waiter_repository import WaiterRepository


class FeedbackServiceRepository(DynamoRepository[FeedbackService]):
    """CRUD repository for FeedbackService entities."""

    _WAITER_ID_INDEX = "waiter_id_index"

    def __init__(
        self,
        settings: AppConfig | None = None,
        waiter_repository: WaiterRepository | None = None,
    ) -> None:
        """Initialise with the feedback-service table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.
            waiter_repository: WaiterRepository instance for waiter lookups; created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.feedback_service_table, FeedbackService, cfg)
        self._waiter_repository = waiter_repository or WaiterRepository(cfg)

    def find_by_waiter_id_and_period(
        self,
        waiter_id: UUID,
        period_start: date,
        period_end: date,
    ) -> list[FeedbackService]:
        """Return service feedback for a waiter within a date range via GSI BETWEEN query.

        Args:
            waiter_id: UUID of the waiter.
            period_start: Inclusive start date (UTC).
            period_end: Inclusive end date (UTC).

        """
        start_str = f"{period_start.isoformat()}T00:00:00+00:00"
        end_str = f"{period_end.isoformat()}T23:59:59.999999+00:00"
        return self._paginated_query(
            "waiter_id_index period query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._WAITER_ID_INDEX,
            KeyConditionExpression="waiter_id = :wid AND #dt BETWEEN :start AND :end",
            ExpressionAttributeNames={"#dt": "date"},
            ExpressionAttributeValues={
                ":wid": {"S": str(waiter_id)},
                ":start": {"S": start_str},
                ":end": {"S": end_str},
            },
        )

    def find_by_reservation_id(self, reservation_id: UUID) -> list[FeedbackService]:
        """Return all service feedback entries for a given reservation.

        Args:
            reservation_id: The reservation UUID to filter by.

        Returns:
            List of FeedbackService instances for that reservation.

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
            "Service feedback scanned by reservation",
            reservation_id=str(reservation_id),
            count=len(items),
        )
        return items

    def find_all_by_waiter_id(self, waiter_id: UUID) -> list[FeedbackService]:
        """Return all service feedback entries for a given waiter (no date filter).

        Args:
            waiter_id: UUID of the waiter.

        Returns:
            List of FeedbackService instances for that waiter.

        """
        items = self._paginated_query(
            "waiter_id_index query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._WAITER_ID_INDEX,
            KeyConditionExpression="waiter_id = :wid",
            ExpressionAttributeValues={":wid": {"S": str(waiter_id)}},
        )
        logger.info(
            "Service feedback queried by waiter",
            waiter_id=str(waiter_id),
            count=len(items),
        )
        return items

    def find_by_location_id(self, location_id: UUID) -> list[FeedbackService]:
        """Query service feedback by location via waiter lookup."""
        waiters = self._waiter_repository.find_by_location_id(location_id)
        waiter_ids = [str(waiter.id) for waiter in waiters]

        if not waiter_ids:
            return []

        feedbacks = []
        for waiter_id in waiter_ids:
            feedbacks.extend(
                self._paginated_query(
                    "waiter_id_index query",
                    self._client.query,
                    TableName=self._resolve_table_name(),
                    IndexName=self._WAITER_ID_INDEX,
                    KeyConditionExpression="waiter_id = :waiter_id",
                    ExpressionAttributeValues={":waiter_id": {"S": waiter_id}},
                )
            )
        return feedbacks

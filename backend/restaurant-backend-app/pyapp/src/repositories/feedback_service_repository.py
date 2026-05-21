"""Repository for FeedbackService entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
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

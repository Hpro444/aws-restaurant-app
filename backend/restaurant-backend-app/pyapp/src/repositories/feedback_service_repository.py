"""Repository for FeedbackService entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.feedback import FeedbackService

from repositories.base_repository import DynamoRepository


class FeedbackServiceRepository(DynamoRepository[FeedbackService]):
    """CRUD repository for FeedbackService entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the feedback-service table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.feedback_service_table, FeedbackService, cfg)

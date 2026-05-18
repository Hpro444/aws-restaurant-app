"""Repository for FeedbackCulinary entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.feedback import FeedbackCulinary

from repositories.base_repository import DynamoRepository


class FeedbackCulinaryRepository(DynamoRepository[FeedbackCulinary]):
    """CRUD repository for FeedbackCulinary entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the feedback-culinary table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.feedback_culinary_table, FeedbackCulinary, cfg)

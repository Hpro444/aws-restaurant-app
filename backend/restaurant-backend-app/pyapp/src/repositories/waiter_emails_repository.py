"""Repository for WaiterEmail entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.waiter_emails import WaiterEmail

from repositories.base_repository import DynamoRepository


class WaiterEmailsRepository(DynamoRepository[WaiterEmail]):
    """CRUD repository for waiter-email entities.

    Overrides _pk_field to use ``email`` (str) instead of the default ``id`` (UUID).
    """

    _pk_field = "email"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the waiter-emails table alias from AppConfig.

        Args:
                settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.waiter_emails_table, WaiterEmail, cfg)

"""Repository for Waiter entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.user import Waiter

from repositories.base_repository import DynamoRepository


class WaiterRepository(DynamoRepository[Waiter]):
    """CRUD repository for Waiter entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the waiters table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.waiters_table, Waiter, cfg)

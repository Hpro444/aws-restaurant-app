"""Repository for Admin entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.admin import Admin

from repositories.base_repository import DynamoRepository


class AdminRepository(DynamoRepository[Admin]):
    """CRUD repository for Admin entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the admins table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.admins_table, Admin, cfg)

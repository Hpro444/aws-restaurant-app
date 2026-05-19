"""Repository for AdminEmail entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.admin_email import AdminEmail

from repositories.base_repository import DynamoRepository


class AdminEmailsRepository(DynamoRepository[AdminEmail]):
    """CRUD repository for admin-email entities.

    Overrides _pk_field to use ``email`` (str) instead of the default ``id`` (UUID).
    """

    _pk_field = "email"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the admin-emails table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.admin_emails_table, AdminEmail, cfg)

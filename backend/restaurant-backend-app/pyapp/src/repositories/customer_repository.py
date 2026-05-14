"""Repository for Customer entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.user import Customer

from repositories.base_repository import DynamoRepository


class CustomerRepository(DynamoRepository[Customer]):
    """CRUD repository for Customer entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the customers table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.customers_table, Customer, cfg)

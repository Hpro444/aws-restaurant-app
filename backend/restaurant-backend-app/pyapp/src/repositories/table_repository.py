"""Repository for Table (restaurant table) entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.table import Table

from repositories.base_repository import DynamoRepository


class TableRepository(DynamoRepository[Table]):
    """CRUD repository for Table entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the tables table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.tables_table, Table, cfg)

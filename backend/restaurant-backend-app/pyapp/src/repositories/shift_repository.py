"""Repository for Shift entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.shift import Shift

from repositories.base_repository import DynamoRepository


class ShiftRepository(DynamoRepository[Shift]):
    """CRUD repository for Shift entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the shifts table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.shifts_table, Shift, cfg)

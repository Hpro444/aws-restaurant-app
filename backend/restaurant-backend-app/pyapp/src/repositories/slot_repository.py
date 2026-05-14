"""Repository for Slot entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.slot import Slot

from repositories.base_repository import DynamoRepository


class SlotRepository(DynamoRepository[Slot]):
    """CRUD repository for Slot entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the slots table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.slots_table, Slot, cfg)

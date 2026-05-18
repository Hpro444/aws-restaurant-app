"""Repository for Location entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.location import Location

from repositories.base_repository import DynamoRepository


class LocationRepository(DynamoRepository[Location]):
    """CRUD repository for Location entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the locations table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.locations_table, Location, cfg)

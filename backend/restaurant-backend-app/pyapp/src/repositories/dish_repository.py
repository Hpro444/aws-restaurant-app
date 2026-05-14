"""Repository for Dish entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.dish import Dish

from repositories.base_repository import DynamoRepository


class DishRepository(DynamoRepository[Dish]):
    """CRUD repository for Dish entities."""

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the dishes table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.dishes_table, Dish, cfg)

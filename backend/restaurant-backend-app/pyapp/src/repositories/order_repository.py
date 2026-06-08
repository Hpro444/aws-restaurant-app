"""Repository for Order entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.order import Order

from repositories.base_repository import DynamoRepository


class OrderRepository(DynamoRepository[Order]):
    """CRUD repository for Order entities with reservation-scoped queries."""

    _RESERVATION_INDEX = "reservation_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the orders table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.orders_table, Order, cfg)

    def find_by_reservation_id(self, reservation_id: UUID) -> list[Order]:
        """Return all orders for a reservation via GSI query.

        Args:
            reservation_id: UUID of the reservation to filter by.

        Returns:
            List of Order domain objects belonging to the reservation.

        """
        table_name = self._resolve_table_name()
        orders = self._paginated_query(
            "reservation_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._RESERVATION_INDEX,
            KeyConditionExpression="reservation_id = :rid",
            ExpressionAttributeValues={
                ":rid": {"S": str(reservation_id)},
            },
        )
        logger.info(
            "Orders filtered by reservation",
            reservation_id=str(reservation_id),
            count=len(orders),
        )
        return orders

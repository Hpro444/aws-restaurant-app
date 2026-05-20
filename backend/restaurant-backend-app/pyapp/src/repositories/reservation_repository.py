"""Repository for Reservation entities in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.reservation import Reservation

from repositories.base_repository import DynamoRepository


class ReservationRepository(DynamoRepository[Reservation]):
    """CRUD repository for Reservation entities.

    Slot-availability lookups now live on the :class:`Slot` model via its
    ``status`` field, so this repository no longer needs any custom slot
    queries — plain :class:`DynamoRepository` CRUD is sufficient.
    """

    _CUSTOMER_INDEX = "customer_id_index"
    _WAITER_INDEX = "waiter_id_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the reservations table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.reservations_table, Reservation, cfg)

    def find_by_customer_id(self, customer_id: UUID) -> list[Reservation]:
        """Return reservations owned by a customer via GSI query."""
        table_name = self._resolve_table_name()
        reservations = self._paginated_query(
            "customer_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._CUSTOMER_INDEX,
            KeyConditionExpression="customer_id = :cid",
            ExpressionAttributeValues={
                ":cid": {"S": str(customer_id)},
            },
        )
        logger.info(
            "Reservations filtered by customer",
            customer_id=str(customer_id),
            count=len(reservations),
        )
        return reservations

    def find_by_waiter_id(self, waiter_id: UUID) -> list[Reservation]:
        """Return reservations assigned to a waiter via GSI query."""
        table_name = self._resolve_table_name()
        reservations = self._paginated_query(
            "waiter_id_index query",
            self._client.query,
            TableName=table_name,
            IndexName=self._WAITER_INDEX,
            KeyConditionExpression="waiter_id = :wid",
            ExpressionAttributeValues={
                ":wid": {"S": str(waiter_id)},
            },
        )
        logger.info(
            "Reservations filtered by waiter",
            waiter_id=str(waiter_id),
            count=len(reservations),
        )
        return reservations

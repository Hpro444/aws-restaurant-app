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

    def _find_by_actor_id(
        self,
        *,
        actor_id: UUID,
        index_name: str,
        key_name: str,
        attr_name: str,
        log_context: str,
    ) -> list[Reservation]:
        table_name = self._resolve_table_name()
        reservations = self._paginated_query(
            f"{index_name} query",
            self._client.query,
            TableName=table_name,
            IndexName=index_name,
            KeyConditionExpression=f"{key_name} = :id",
            ExpressionAttributeValues={
                ":id": {"S": str(actor_id)},
            },
        )
        logger.info(
            f"Reservations filtered by {log_context}",
            **{attr_name: str(actor_id)},
            count=len(reservations),
        )
        return reservations

    def find_by_customer_id(self, customer_id: UUID) -> list[Reservation]:
        """Return reservations owned by a customer via GSI query."""
        return self._find_by_actor_id(
            actor_id=customer_id,
            index_name=self._CUSTOMER_INDEX,
            key_name="customer_id",
            attr_name="customer_id",
            log_context="customer",
        )

    def find_by_waiter_id(self, waiter_id: UUID) -> list[Reservation]:
        """Return reservations assigned to a waiter via GSI query."""
        return self._find_by_actor_id(
            actor_id=waiter_id,
            index_name=self._WAITER_INDEX,
            key_name="waiter_id",
            attr_name="waiter_id",
            log_context="waiter",
        )

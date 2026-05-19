"""Repository for Reservation entities in DynamoDB."""

from __future__ import annotations

from commons.app_config import AppConfig
from domain.reservation import Reservation

from repositories.base_repository import DynamoRepository


class ReservationRepository(DynamoRepository[Reservation]):
    """CRUD repository for Reservation entities.

    Slot-availability lookups now live on the :class:`Slot` model via its
    ``status`` field, so this repository no longer needs any custom slot
    queries — plain :class:`DynamoRepository` CRUD is sufficient.
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the reservations table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.reservations_table, Reservation, cfg)

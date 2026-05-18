"""Repository for Reservation entities in DynamoDB."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.reservation import Reservation
from enums.reservation_status import ReservationStatus

from repositories.base_repository import DynamoRepository


class ReservationRepository(DynamoRepository[Reservation]):
    """CRUD repository for Reservation entities with slot-based queries."""

    _SLOT_INDEX = "slot-index"
    _ACTIVE_STATUSES = {ReservationStatus.RESERVED, ReservationStatus.IN_PROGRESS}

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the reservations table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.reservations_table, Reservation, cfg)

    def is_slot_booked(self, slot_id: UUID) -> bool:
        """Check whether a slot has an active reservation.

        Queries the ``slot-index`` GSI for the given slot_id and checks
        the status of the returned item. Returns True if an active reservation
        (RESERVED or IN_PROGRESS) exists for this slot.

        Note: Limit=1 without FilterExpression ensures we read exactly one
        item before applying filter logic in Python (Limit + Filter together
        would apply Limit before Filter, causing incorrect results).

        Args:
            slot_id: UUID of the slot to check.

        Returns:
            True if an active reservation exists for this slot.

        """
        table_name = self._resolve_table_name()
        params: dict[str, Any] = {
            "TableName": table_name,
            "IndexName": self._SLOT_INDEX,
            "KeyConditionExpression": "slot = :sid",
            "ExpressionAttributeValues": {
                ":sid": {"S": str(slot_id)},
            },
            "Limit": 1,  # Slot should have at most one reservation
        }

        try:
            response = self._client.query(**params)
            items = response.get("Items", [])
            if not items:
                return False

            # Deserialize and check if the reservation is active
            reservation = self._model_class.from_dynamodb_item(items[0])
            return reservation.status in self._ACTIVE_STATUSES
        except ClientError as exc:
            logger.error(
                "Query on slot-index failed",
                slot_id=str(slot_id),
                error=str(exc),
            )
            return False

    def find_booked_slot_ids(self, slot_ids: set[UUID]) -> set[UUID]:
        """Return the subset of slot_ids that have an active reservation.

        Queries the ``slot-index`` GSI once per slot. Each query reads
        at most 1 item (a slot has 0 or 1 active reservation), making
        this very efficient per call.

        For N slots this is N DynamoDB queries. Typical N = 7–21 for
        a single-location availability check.

        Args:
            slot_ids: Set of slot UUIDs to check.

        Returns:
            Set of slot UUIDs that are currently booked.

        """
        booked: set[UUID] = set()
        for sid in slot_ids:
            if self.is_slot_booked(sid):
                booked.add(sid)

        logger.info(
            "Booked slots identified",
            checked=len(slot_ids),
            booked=len(booked),
        )
        return booked

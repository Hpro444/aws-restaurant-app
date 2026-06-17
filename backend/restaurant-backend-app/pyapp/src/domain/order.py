"""Domain model for an order persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel
from pydantic import AwareDatetime

from domain.order_item import OrderItem


class Order(DynamoModel):
    """Represents a waiter-created order linked to a specific reservation.

    ``items`` holds every dish line item; the list must contain at least one
    entry. Serialisation via ``model_dump(mode='json')`` converts nested
    ``OrderItem`` instances to plain dicts, which ``TypeSerializer`` stores as
    a DynamoDB List-of-Maps and ``TypeDeserializer`` reconstructs on read.
    """

    _exclude_none = True

    id: UUID
    reservation_id: UUID
    waiter_id: UUID
    items: list[OrderItem]
    created_at: AwareDatetime

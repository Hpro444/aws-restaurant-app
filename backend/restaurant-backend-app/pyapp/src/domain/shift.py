"""Domain model for a waiter shift persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class Shift(DynamoModel):
    """Represents one location shift with assigned waiters and slots."""

    id: UUID
    location_id: UUID
    waiter_ids: list[UUID]
    slot_ids: list[UUID]

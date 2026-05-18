"""Domain model for a waiter shift persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class Shift(DynamoModel):
    """Represents a work shift for a waiter."""

    id: UUID
    waiter_id: UUID
    slots: list[UUID]

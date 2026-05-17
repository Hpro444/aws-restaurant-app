"""Domain model for waiter-email records persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class WaiterEmail(DynamoModel):
    """Represents a waiter email address with associated restaurant for role assignment.

    The primary key is ``email`` (str), not the default ``id`` (UUID).
    This table acts as an allow-list for waiter role assignment.
    """

    email: str
    location_id: UUID

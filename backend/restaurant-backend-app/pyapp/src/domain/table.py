"""Domain model for a restaurant table persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class Table(DynamoModel):
    """Represents a physical table in a restaurant location."""

    id: UUID
    table_number: int
    capacity: int
    restaurant_id: UUID

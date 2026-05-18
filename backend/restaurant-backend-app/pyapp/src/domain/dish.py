"""Domain model for a dish persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class Dish(DynamoModel):
    """Represents a dish served at a restaurant location."""

    id: UUID
    location_id: UUID
    name: str
    description: str
    image_url: str
    price: float
    weight_gram: int

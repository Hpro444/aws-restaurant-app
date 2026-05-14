"""Domain model for a restaurant location persisted in DynamoDB."""

from __future__ import annotations

from datetime import time
from uuid import UUID

from commons.dynamo_model import DynamoModel


class Location(DynamoModel):
    """Represents a restaurant location business entity."""

    id: UUID
    name: str
    address: str
    description: str
    image_url: str
    open_time: time
    close_time: time

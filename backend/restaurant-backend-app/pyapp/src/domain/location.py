"""Domain model for a restaurant location persisted in DynamoDB."""

from __future__ import annotations

from datetime import time
from uuid import UUID

from commons.dynamo_model import DynamoModel
from pydantic import field_validator


class Location(DynamoModel):
    """Represents a restaurant location business entity."""

    id: UUID
    name: str
    address: str
    description: str
    image_url: str
    open_time: time
    close_time: time

    @field_validator("open_time", "close_time", mode="before")
    @classmethod
    def parse_time_strings(cls, time_value: object) -> object:
        """Convert 'HH:MM' strings to time objects for DynamoDB deserialization."""
        if isinstance(time_value, str):
            try:
                return time.fromisoformat(time_value)
            except ValueError:
                # If fromisoformat fails, let Pydantic's default validator handle it
                pass
        return time_value

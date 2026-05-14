"""Domain model for a restaurant table slot persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel
from pydantic import AwareDatetime


class Slot(DynamoModel):
    """Represents a time slot for a restaurant table."""

    id: UUID
    table_id: UUID
    start_time: AwareDatetime
    end_time: AwareDatetime
    date: AwareDatetime

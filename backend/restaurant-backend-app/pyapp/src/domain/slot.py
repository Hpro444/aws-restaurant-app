"""Domain model for a restaurant table slot persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel
from enums import SlotStatus
from pydantic import AwareDatetime


class Slot(DynamoModel):
    """Represents a fixed 90-minute time slot for a restaurant table.

    ``status`` defaults to :attr:`SlotStatus.FREE` and is flipped to
    :attr:`SlotStatus.RESERVED` when a reservation claims the slot.
    """

    id: UUID
    table_id: UUID
    waiter_id: UUID | None = None
    start_time: AwareDatetime
    end_time: AwareDatetime
    date: AwareDatetime
    status: SlotStatus = SlotStatus.FREE

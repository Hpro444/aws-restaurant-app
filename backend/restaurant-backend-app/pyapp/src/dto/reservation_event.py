"""DTOs for SQS reservation lifecycle events."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from dto.reservation_management import ReservationView


class ReservationEventType(str, Enum):
    """Lifecycle event types published to the reservation SQS queue."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReservationEventMessage(BaseModel):
    """Envelope published to the reservation events SQS queue."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_type: ReservationEventType = Field(..., alias="eventType")
    reservation: ReservationView
    timestamp: str = Field(
        ..., description="ISO-8601 UTC string, e.g. 2026-06-01T12:00:00Z"
    )

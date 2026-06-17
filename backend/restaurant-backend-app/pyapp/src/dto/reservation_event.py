"""DTOs for SQS reservation lifecycle events."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from dto.reservation_management import AllowedActions


class ReservationEventType(str, Enum):
    """Lifecycle event types published to the reservation SQS queue."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class ReservationEventMessage(BaseModel):
    """Flat envelope published to the reservation events SQS queue.

    All reservation fields are inlined (no nested sub-object) so consumers
    can process the message without additional unwrapping.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_type: ReservationEventType = Field(..., alias="eventType")
    timestamp: str = Field(
        ..., description="ISO-8601 UTC string, e.g. 2026-06-01T12:00:00Z"
    )

    reservation_id: str = Field(..., alias="reservationId")
    status: str
    customer_id: str | None = Field(None, alias="customerId")
    waiter_id: str | None = Field(None, alias="waiterId")
    location_id: str | None = Field(None, alias="locationId")
    location_address: str | None = None
    table_number: int | None = Field(None, alias="tableNumber")
    date: str
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")
    guests_number: int = Field(..., alias="guestsNumber")
    allowed_actions: AllowedActions = Field(..., alias="allowedActions")
    cutoff_reason: str | None = Field(None, alias="cutoffReason")

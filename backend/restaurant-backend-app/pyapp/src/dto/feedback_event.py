"""DTOs for SQS feedback lifecycle events."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FeedbackEventType(str, Enum):
    """Lifecycle event types published to the feedback SQS queue."""

    CREATED = "CREATED"


class FeedbackEventMessage(BaseModel):
    """Flat envelope published to the feedback events SQS queue."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_type: FeedbackEventType = Field(..., alias="eventType")
    feedback_id: str = Field(..., alias="feedbackId")
    reservation_id: str | None = Field(None, alias="reservationId")
    customer_id: str | None = Field(None, alias="customerId")
    feedback: str
    rate: int | None = None
    date: str = Field(..., description="ISO-8601 UTC string")
    user_name: str | None = Field(None, alias="userName")
    user_image_url: str | None = Field(None, alias="userImageUrl")
    feedback_type: str = Field(..., alias="feedbackType")
    location_id: str | None = Field(None, alias="locationId")
    location_address: str | None = Field(None, alias="locationAddress")
    waiter_id: str | None = Field(None, alias="waiterId")
    timestamp: str = Field(..., description="ISO-8601 UTC string")

"""Domain models for feedback persisted in DynamoDB."""

from __future__ import annotations

from abc import ABC
from uuid import UUID

from commons.dynamo_model import DynamoModel
from pydantic import AwareDatetime


class Feedback(DynamoModel, ABC):
    """Base class for feedback models; must be subclassed as FeedbackCuisine or FeedbackService."""

    id: UUID
    reservation_id: UUID | None = None
    customer_id: UUID | None
    feedback: str
    rate: int | None = None
    date: AwareDatetime
    user_name: str | None = None
    user_image_url: str | None = None


class FeedbackCuisine(Feedback):
    """Represents feedback related to culinary experience."""

    location_id: UUID


class FeedbackService(Feedback):
    """Represents feedback related to service experience."""

    waiter_id: UUID

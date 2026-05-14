"""Domain models for feedback persisted in DynamoDB."""

from __future__ import annotations

from abc import ABC
from uuid import UUID

from commons.dynamo_model import DynamoModel


class Feedback(DynamoModel, ABC):
    """Base class for feedback models; must be subclassed as FeedbackCulinary or FeedbackService."""

    id: UUID
    customer_id: UUID | None
    feedback: str


class FeedbackCulinary(Feedback):
    """Represents feedback related to culinary experience."""

    location_id: UUID


class FeedbackService(Feedback):
    """Represents feedback related to service experience."""

    waiter_id: UUID

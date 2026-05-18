"""Abstract domain model for user profiles persisted in DynamoDB."""

from __future__ import annotations

from abc import ABC
from uuid import UUID

from commons.dynamo_model import DynamoModel


class User(DynamoModel, ABC):
    """Shared fields for user domain models; must be subclassed as Customer or Waiter."""

    id: UUID
    fname: str
    lname: str
    email: str
    image_url: str


class Customer(User):
    """Represents a logged-in customer profile."""


class Waiter(User):
    """Represents a logged-in waiter profile linked to a restaurant."""

    location_id: UUID

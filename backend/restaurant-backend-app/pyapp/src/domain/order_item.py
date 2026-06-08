"""Domain model for a single line item within an order."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class OrderItem(BaseModel):
    """A dish and the quantity ordered for it."""

    dish_id: UUID
    quantity: int

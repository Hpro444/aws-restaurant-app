"""DTOs for the POST /orders endpoint."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemRequest(BaseModel):
    """A single dish line item in an order request."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    dish_id: UUID = Field(..., alias="dishId")
    quantity: int = Field(..., gt=0)


class CreateOrderRequest(BaseModel):
    """Validated request body for creating a waiter order."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservation_id: UUID = Field(..., alias="reservationId")
    items: list[OrderItemRequest] = Field(..., min_length=1)


class CreateOrderResponse(BaseModel):
    """Payload returned on a successful order creation."""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str = Field(..., alias="orderId")
    reservation_id: str = Field(..., alias="reservationId")

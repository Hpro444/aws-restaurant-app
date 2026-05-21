"""DTOs for the GET /dishes/popular endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DishResponse(BaseModel):
    """A single dish returned in the popular dishes list.

    Represents a dish with all attributes needed for display and ordering.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    image_url: str
    price: float
    weight_gram: int

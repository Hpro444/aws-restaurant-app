"""DTOs for dish endpoints."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from enums.dish_type import DishType
from pydantic import BaseModel, ConfigDict


class DishSort(str, Enum):
    """Valid sort options for the GET /dishes endpoint."""

    POPULARITY_ASC = "popularity,asc"
    POPULARITY_DESC = "popularity,desc"
    PRICE_ASC = "price,asc"
    PRICE_DESC = "price,desc"


class DishDietaryFilter(str, Enum):
    """Valid dietary filter options for the GET /dishes endpoint."""

    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    GLUTEN_FREE = "GLUTEN_FREE"
    DAIRY_FREE = "DAIRY_FREE"


class GetDishesRequest(BaseModel):
    """Validated query parameters for GET /dishes.

    Both parameters are optional. Validation fails with 422 when
    an unrecognised ``dishType``, ``sort`` or ``filter_dietary`` value is provided.
    """

    model_config = ConfigDict(extra="ignore")

    dishType: Optional[DishType] = None
    sort: Optional[DishSort] = None
    dietary_filter: Optional[DishDietaryFilter] = None


class DishResponse(BaseModel):
    """A single dish returned by any dish endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    description: str
    image_url: str
    price: float
    weight_gram: int
    state: str

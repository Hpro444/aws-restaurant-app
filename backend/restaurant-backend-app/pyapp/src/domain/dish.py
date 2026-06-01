"""Domain model for a dish persisted in DynamoDB."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commons.dynamo_model import DynamoModel
from enums.dish_state import DishState
from enums.dish_type import DishType


class Dish(DynamoModel):
    """Represents a dish served at a restaurant location."""

    id: UUID
    location_id: UUID
    name: str
    description: str
    image_url: str
    price: float
    weight_gram: int
    specialty: bool = False
    popular: bool = False
    state: DishState = DishState.AVAILABLE
    dish_type: DishType = DishType.MAIN_COURSE

    def to_dynamodb_item(self) -> dict[str, Any]:
        """Serialize the dish and coerce ``popular`` to numeric for GSI compatibility.

        DynamoDB secondary index keys cannot use the BOOL type, so the table
        stores ``popular`` as 1/0 (Number) while the domain model keeps it as bool.
        """
        item = super().to_dynamodb_item()
        item["popular"] = {"N": "1" if self.popular else "0"}
        return item

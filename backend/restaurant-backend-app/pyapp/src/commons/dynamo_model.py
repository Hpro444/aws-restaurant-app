"""Pydantic base model with DynamoDB low-level serialization/deserialization."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar, Self

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel, ConfigDict, field_validator

dynamo_deserializer = TypeDeserializer()
dynamo_serializer = TypeSerializer()


class DynamoModel(BaseModel):
    """Pydantic base that handles DynamoDB low-level ↔ Python round-trips.

    Subclasses get to_dynamodb_item / from_dynamodb_item for free.
    Numeric fields deserialized from DynamoDB arrive as Decimal; the
    field validator converts them to int or float before Pydantic validates.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _exclude_none: ClassVar[bool] = False

    @field_validator("*", mode="before")
    @classmethod
    def _convert_decimals(cls, v: object) -> object:
        """Convert Decimal (returned by TypeDeserializer for N fields) to int or float."""
        if isinstance(v, Decimal):
            return int(v) if v % 1 == 0 else float(v)
        return v

    def to_dynamodb_item(self) -> dict[str, Any]:
        """Serialize this model to a DynamoDB low-level item map."""
        return {
            k: dynamo_serializer.serialize(
                Decimal(str(v)) if isinstance(v, float) else v
            )
            for k, v in self.model_dump(
                mode="json", exclude_none=self._exclude_none
            ).items()
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict[str, Any]) -> Self:
        """Build this model from a DynamoDB low-level item map."""
        python_dict = {k: dynamo_deserializer.deserialize(v) for k, v in item.items()}
        return cls.model_validate(python_dict)

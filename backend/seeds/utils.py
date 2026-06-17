"""Shared utilities for seed modules."""

from decimal import Decimal
from uuid import UUID, uuid5

from seeds.config import SEED_NAMESPACE


def seed_id(entity_type: str, natural_key: str) -> UUID:
    """Generate deterministic UUID5 for reproducible seeding."""
    return uuid5(SEED_NAMESPACE, f"{entity_type}:{natural_key}")


def to_item(model) -> dict:
    """Serialize a domain model to a DynamoDB high-level dict.

    Converts float values to Decimal, which boto3 requires for numeric attributes.
    """
    return {
        k: Decimal(str(v)) if isinstance(v, float) else v
        for k, v in model.model_dump(mode="json", exclude_none=True).items()
    }

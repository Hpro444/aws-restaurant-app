"""Pydantic models for structured error responses."""

from pydantic import BaseModel, ConfigDict


class FieldError(BaseModel):
    """A single field-level validation error."""

    model_config = ConfigDict(extra="ignore")

    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    """Wrapper returned on 422 responses, containing one or more field errors."""

    model_config = ConfigDict(extra="ignore")

    errors: list[FieldError]

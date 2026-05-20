"""Pydantic models for structured error responses."""

from pydantic import BaseModel


class FieldError(BaseModel):
    """A single field-level validation error."""

    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    """Wrapper returned on 422 responses, containing one or more field errors."""

    errors: list[FieldError]

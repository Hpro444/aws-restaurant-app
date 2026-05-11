"""Pydantic model for the user registration success response."""

from pydantic import BaseModel


class SignUpResponse(BaseModel):
    """Payload returned on successful user registration."""

    userId: str
    message: str

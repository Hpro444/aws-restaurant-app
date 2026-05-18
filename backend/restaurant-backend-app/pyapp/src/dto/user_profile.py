"""Pydantic models for user profile responses."""

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    """Profile payload returned for the authenticated user."""

    first_name: str
    last_name: str
    image_url: str
    email: str
    role: str

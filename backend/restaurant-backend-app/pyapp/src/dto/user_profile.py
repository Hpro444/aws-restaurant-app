"""Pydantic models for user profile requests and responses."""

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    """Profile payload returned for the authenticated user."""

    first_name: str
    last_name: str
    image_url: str
    email: str
    role: str


class UpdateProfileRequest(BaseModel):
    """Payload for updating a user's own profile fields."""

    first_name: str
    last_name: str
    image_url: str

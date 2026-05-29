"""Pydantic models for user profile requests and responses."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileResponse(BaseModel):
    """Profile payload returned for the authenticated user."""

    model_config = ConfigDict(extra="ignore")

    first_name: str
    last_name: str
    image_url: str
    email: str
    role: str


class UpdateProfileRequest(BaseModel):
    """Payload for updating a user's own profile fields."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    image_url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, image_url_value: str) -> str:
        """Reject image_url values that are not http(s) URLs."""
        if not (
            image_url_value.startswith("http://")
            or image_url_value.startswith("https://")
        ):
            raise ValueError("must be an http:// or https:// URL")
        return image_url_value

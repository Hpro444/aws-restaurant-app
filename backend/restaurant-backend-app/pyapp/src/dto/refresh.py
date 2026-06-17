"""Pydantic models for the token refresh request and response."""

from pydantic import BaseModel, ConfigDict, Field


class RefreshRequest(BaseModel):
    """Validated payload accepted by POST /auth/refresh."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    """Payload returned on successful token refresh."""

    model_config = ConfigDict(extra="ignore")

    access_token: str

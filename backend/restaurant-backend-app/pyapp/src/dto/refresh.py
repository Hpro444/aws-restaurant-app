"""Pydantic models for the token refresh request and response."""

from pydantic import BaseModel, ConfigDict


class RefreshRequest(BaseModel):
    """Validated payload accepted by POST /auth/refresh."""

    model_config = ConfigDict(extra="ignore")

    refresh_token: str


class RefreshResponse(BaseModel):
    """Payload returned on successful token refresh."""

    model_config = ConfigDict(extra="ignore")

    access_token: str

"""Pydantic models for the token refresh request and response."""

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    """Validated payload accepted by POST /auth/refresh."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Payload returned on successful token refresh."""

    access_token: str

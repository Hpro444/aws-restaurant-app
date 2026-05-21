"""DTOs for the POST /auth/logout endpoint."""

from pydantic import BaseModel, ConfigDict


class LogoutRequest(BaseModel):
    """Request body carrying the refresh token to revoke."""

    model_config = ConfigDict(extra="ignore")

    refresh_token: str


class LogoutResponse(BaseModel):
    """Confirmation payload returned on successful logout."""

    model_config = ConfigDict(extra="ignore")

    message: str

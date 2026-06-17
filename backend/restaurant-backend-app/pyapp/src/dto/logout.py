"""DTOs for the POST /auth/logout endpoint."""

from pydantic import BaseModel, ConfigDict, Field


class LogoutRequest(BaseModel):
    """Request body carrying the refresh token to revoke."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(BaseModel):
    """Confirmation payload returned on successful logout."""

    model_config = ConfigDict(extra="ignore")

    message: str

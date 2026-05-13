"""DTOs for the POST /auth/logout endpoint."""

from pydantic import BaseModel


class LogoutRequest(BaseModel):
    """Request body carrying the refresh token to revoke."""

    refresh_token: str


class LogoutResponse(BaseModel):
    """Confirmation payload returned on successful logout."""

    message: str

"""Pydantic model carrying the result of a successful authentication."""

from pydantic import BaseModel


class AuthResult(BaseModel):
    """Returned by CognitoService.authenticate_user; carries all fields needed for the sign-in response."""

    access_token: str
    refresh_token: str
    username: str
    role: str

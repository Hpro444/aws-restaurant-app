"""Pydantic model carrying the result of a successful authentication."""

from pydantic import BaseModel, ConfigDict


class AuthResult(BaseModel):
    """Returned by CognitoService.authenticate_user; carries all fields needed for the sign-in response."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str
    username: str
    role: str

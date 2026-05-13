"""Dataclass carrying the result of a successful authentication."""

from dataclasses import dataclass


@dataclass
class AuthResult:
    """Returned by CognitoService.authenticate_user; carries all fields needed for the sign-in response."""

    access_token: str
    refresh_token: str
    username: str
    role: str

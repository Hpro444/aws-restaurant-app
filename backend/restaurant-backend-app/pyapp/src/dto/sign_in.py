"""Pydantic models for the sign-in request and response."""

from pydantic import BaseModel, EmailStr, SecretStr


class SignInRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-in."""

    email: EmailStr
    password: SecretStr


class SignInResponse(BaseModel):
    """Payload returned on successful authentication."""

    access_token: str
    refresh_token: str
    username: str
    role: str

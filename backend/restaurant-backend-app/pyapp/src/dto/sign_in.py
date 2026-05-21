"""Pydantic models for the sign-in request and response."""

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, field_validator


class SignInRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-in."""

    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: object) -> object:
        """Strip whitespace and lowercase the email before format validation."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class SignInResponse(BaseModel):
    """Payload returned on successful authentication."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str
    username: str
    role: str

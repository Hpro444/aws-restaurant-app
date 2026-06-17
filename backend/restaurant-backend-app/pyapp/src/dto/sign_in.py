"""Pydantic models for the sign-in request and response."""

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, field_validator


class SignInRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-in."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    email: EmailStr
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email_value: object) -> object:
        """Strip whitespace and lowercase the email before format validation."""
        if isinstance(email_value, str):
            return email_value.strip().lower()
        return email_value

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, password_value: SecretStr) -> SecretStr:
        """Reject empty/whitespace-only passwords."""
        if not password_value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return password_value


class SignInResponse(BaseModel):
    """Payload returned on successful authentication."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str
    username: str
    role: str

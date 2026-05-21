"""Pydantic models for the sign-up request and response."""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class SignUpRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-up."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", str_strip_whitespace=True
    )

    first_name: str = Field(..., alias="firstName", min_length=1, max_length=100)
    last_name: str = Field(..., alias="lastName", min_length=1, max_length=100)
    email: EmailStr
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: object) -> object:
        """Strip whitespace and lowercase the email, then enforce that the local part starts with a letter."""
        if isinstance(v, str):
            v = v.strip().lower()
            local = v.split("@")[0]
            if not local or not local[0].isalpha():
                raise ValueError("email local part must start with a letter")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: SecretStr) -> SecretStr:
        """Enforce password complexity: 8–16 chars, upper, lower, digit, special char."""
        raw = v.get_secret_value()
        violations = []
        if not (8 <= len(raw) <= 16):
            violations.append("must be 8–16 characters")
        if not re.search(r"[A-Z]", raw):
            violations.append("must contain at least one uppercase letter")
        if not re.search(r"[a-z]", raw):
            violations.append("must contain at least one lowercase letter")
        if not re.search(r"\d", raw):
            violations.append("must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", raw):
            violations.append("must contain at least one special character")
        if violations:
            raise ValueError(", ".join(violations))
        return v


class SignUpResponse(BaseModel):
    """Payload returned on successful user registration."""

    model_config = ConfigDict(extra="ignore")

    message: str

"""Pydantic model for the user registration request body."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignUpRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-up."""

    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        """Trim whitespace and lowercase the email before validation."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        """Enforce password complexity: 8–16 chars, upper, lower, digit, special char."""
        violations = []
        if not (8 <= len(v) <= 16):
            violations.append("must be 8–16 characters")
        if not re.search(r"[A-Z]", v):
            violations.append("must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            violations.append("must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            violations.append("must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            violations.append("must contain at least one special character")
        if violations:
            raise ValueError(", ".join(violations))
        return v

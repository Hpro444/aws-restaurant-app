"""Pydantic model for the user registration request body."""

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    """Validated payload accepted by POST /auth/sign-up."""

    firstName: str = Field(..., min_length=1)
    lastName: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)

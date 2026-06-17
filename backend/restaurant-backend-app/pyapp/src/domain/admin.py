"""Domain model for admin user profiles persisted in DynamoDB."""

from __future__ import annotations

from domain.user import User


class Admin(User):
    """Represents an admin user profile with the same fields as a customer."""

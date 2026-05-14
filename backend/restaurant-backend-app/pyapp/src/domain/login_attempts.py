"""Domain model for per-email login attempt tracking persisted in DynamoDB."""

from __future__ import annotations

from commons.dynamo_model import DynamoModel


class LoginAttempts(DynamoModel):
    """Tracks failed login attempts and optional lockout for a given email address.

    The primary key is ``email`` (str), not the standard ``id`` (UUID).
    ``_exclude_none = True`` ensures ``lockout_until`` is omitted from the
    serialized item when absent — DynamoDB TTL requires a Number, never NULL.
    """

    _exclude_none = True

    email: str
    failed_attempts: int = 0
    lockout_until: int | None = None

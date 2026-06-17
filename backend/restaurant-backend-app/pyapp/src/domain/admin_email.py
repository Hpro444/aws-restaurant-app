"""Domain model for admin-email records persisted in DynamoDB."""

from __future__ import annotations

from commons.dynamo_model import DynamoModel


class AdminEmail(DynamoModel):
    """Represents an admin email address used as an allow-list for admin role assignment.

    The primary key is ``email`` (str), not the default ``id`` (UUID).
    """

    email: str

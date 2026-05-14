"""Repository for LoginAttempts entities in DynamoDB."""

from __future__ import annotations

from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.login_attempts import LoginAttempts

from repositories.base_repository import DynamoRepository


class LoginAttemptsRepository(DynamoRepository[LoginAttempts]):
    """CRUD and domain-specific operations for the login-attempts DynamoDB table.

    Overrides _pk_field to use ``email`` (str) instead of the default ``id`` (UUID).
    """

    _pk_field = "email"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the login-attempts table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.login_attempts_table, LoginAttempts, cfg)

    def get_lockout_until(self, email: str) -> int | None:
        """Return the lockout_until Unix timestamp, or None if the field is absent.

        Uses a projection so only the TTL field is transferred from DynamoDB.

        Args:
            email: The user's email address used as the partition key.

        """
        try:
            response = self._client.get_item(
                TableName=self._resolve_table_name(),
                Key={"email": {"S": email}},
                ProjectionExpression="lockout_until",
            )
        except ClientError as exc:
            logger.error(
                "DynamoDB get_item (lockout) failed", email=email, error=str(exc)
            )
            return None

        raw = response.get("Item", {}).get("lockout_until")
        return int(raw["N"]) if raw else None

    def increment_failed_attempts(self, email: str) -> int:
        """Atomically increment the failed_attempts counter and return the new value.

        Uses update_item ADD to safely handle concurrent increments.

        Args:
            email: The user's email address used as the partition key.

        """
        try:
            response = self._client.update_item(
                TableName=self._resolve_table_name(),
                Key={"email": {"S": email}},
                UpdateExpression="ADD failed_attempts :inc",
                ExpressionAttributeValues={":inc": {"N": "1"}},
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as exc:
            logger.error(
                "DynamoDB update_item (increment) failed", email=email, error=str(exc)
            )
            return 0

        return int(response["Attributes"]["failed_attempts"]["N"])

    def set_lockout(self, email: str, lockout_until: int) -> None:
        """Write the lockout_until TTL timestamp for the given email.

        Args:
            email: The user's email address used as the partition key.
            lockout_until: Unix timestamp (seconds) when the lockout expires.

        """
        try:
            self._client.update_item(
                TableName=self._resolve_table_name(),
                Key={"email": {"S": email}},
                UpdateExpression="SET lockout_until = :lu",
                ExpressionAttributeValues={":lu": {"N": str(lockout_until)}},
            )
        except ClientError as exc:
            logger.error(
                "DynamoDB update_item (lockout) failed", email=email, error=str(exc)
            )

    def reset_attempts(self, email: str) -> None:
        """Delete the attempt record for the given email, clearing counter and lockout.

        Args:
            email: The user's email address used as the partition key.

        """
        self.delete(email)

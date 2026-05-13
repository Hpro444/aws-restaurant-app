"""DynamoDB-backed service for tracking per-email failed login attempts."""

import time

import boto3
from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.log_helper import logger


class LoginAttemptsService:
    """Tracks failed login attempts per email in DynamoDB and enforces account lockout.

    Each email maps to a single DynamoDB item with:
    - ``failed_attempts`` (Number): atomically incremented on each failure.
    - ``lockout_until`` (Number, Unix timestamp): set when the attempt ceiling is
      reached and doubles as the DynamoDB TTL so the item is auto-deleted after
      the lockout window expires.

    The actual table name is resolved at runtime by listing DynamoDB tables and
    finding the one whose name contains the configured alias (e.g. ``login-attempts``
    resolves to ``tm3-login-attempts-dev`` in the deployed environment).
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise the service with DynamoDB client and lockout config.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        self._table_alias = cfg.login_attempts_table
        self._resolved_table_name: str | None = None
        self._max_attempts = cfg.max_login_attempts
        self._lockout_seconds = cfg.lockout_seconds
        self._client = boto3.client("dynamodb", region_name=cfg.aws_region)

    @property
    def max_attempts(self) -> int:
        """Return the maximum allowed failed attempts before lockout."""
        return self._max_attempts

    def _resolve_table_name(self) -> str:
        """Return the actual DynamoDB table name, resolving it by alias on first call.

        Paginates ``list_tables`` until a table whose name contains ``_table_alias``
        is found, then caches the result for the lifetime of the Lambda context.
        Falls back to the raw alias when no matching table is found (e.g. local tests).

        Returns:
            The fully-qualified table name as deployed (e.g. ``tm3-login-attempts-dev``).

        """
        if self._resolved_table_name:
            return self._resolved_table_name

        logger.info("Resolving DynamoDB table name", alias=self._table_alias)
        last_evaluated = None

        while True:
            params: dict = {"Limit": 100}
            if last_evaluated:
                params["ExclusiveStartTableName"] = last_evaluated

            try:
                response = self._client.list_tables(**params)
            except ClientError as exc:
                logger.error("list_tables failed", error=str(exc))
                break

            for name in response.get("TableNames", []):
                if self._table_alias in name:
                    self._resolved_table_name = name
                    logger.info(
                        "Resolved table name", alias=self._table_alias, table=name
                    )
                    return name

            last_evaluated = response.get("LastEvaluatedTableName")
            if not last_evaluated:
                break

        logger.info("No table found, falling back to alias", alias=self._table_alias)
        self._resolved_table_name = self._table_alias
        return self._table_alias

    def get_lockout_until(self, email: str) -> int | None:
        """Return the lockout expiry Unix timestamp if the account is locked, else None.

        An account is considered locked when ``lockout_until`` exists in its record
        and its value is strictly greater than the current time. When an expired
        lockout is found, the item is deleted immediately so the attempt counter
        resets — DynamoDB TTL cleanup is not instant and can lag by hours.

        Args:
            email: The user's email address used as the DynamoDB partition key.

        Returns:
            Unix timestamp (seconds) when the lockout expires, or ``None`` if the
            account is not locked.

        """
        try:
            response = self._client.get_item(
                TableName=self._resolve_table_name(),
                Key={"email": {"S": email}},
                ProjectionExpression="lockout_until",
            )
        except ClientError as exc:
            logger.error("DynamoDB get_item failed", email=email, error=str(exc))
            return None

        raw = response.get("Item", {}).get("lockout_until")
        if raw is None:
            return None

        ts = int(raw["N"])
        logger.debug("Lockout check", current_time=int(time.time()), lockout_until=ts)
        if ts > int(time.time()):
            return ts

        logger.info("Lockout expired, resetting attempt counter", email=email)
        self.reset_attempts(email)
        return None

    def increment_failed_attempts(self, email: str) -> tuple[int, int | None]:
        """Atomically increment the failed-attempt counter for the given email.

        When the new count reaches ``max_attempts``, a lockout timestamp is written
        to DynamoDB and returned to the caller. DynamoDB TTL on ``lockout_until``
        ensures the item is auto-deleted once the lockout window expires.

        Args:
            email: The user's email address used as the DynamoDB partition key.

        Returns:
            A ``(new_count, lockout_until)`` tuple where ``lockout_until`` is a Unix
            timestamp if the account just became locked, or ``None`` otherwise.

        """
        table = self._resolve_table_name()
        try:
            response = self._client.update_item(
                TableName=table,
                Key={"email": {"S": email}},
                UpdateExpression="ADD failed_attempts :inc",
                ExpressionAttributeValues={":inc": {"N": "1"}},
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as exc:
            logger.error(
                "DynamoDB update_item (increment) failed", email=email, error=str(exc)
            )
            return 0, None

        new_count = int(response["Attributes"]["failed_attempts"]["N"])
        logger.info("Failed login attempt recorded", email=email, attempts=new_count)

        if new_count < self._max_attempts:
            return new_count, None

        lockout_until = int(time.time()) + self._lockout_seconds
        try:
            self._client.update_item(
                TableName=table,
                Key={"email": {"S": email}},
                UpdateExpression="SET lockout_until = :lu",
                ExpressionAttributeValues={":lu": {"N": str(lockout_until)}},
            )
            logger.info("Account locked", email=email, lockout_until=lockout_until)
        except ClientError as exc:
            logger.error(
                "DynamoDB update_item (lockout) failed", email=email, error=str(exc)
            )

        return new_count, lockout_until

    def reset_attempts(self, email: str) -> None:
        """Delete the attempt record for the given email on successful login.

        Args:
            email: The user's email address used as the DynamoDB partition key.

        """
        try:
            self._client.delete_item(
                TableName=self._resolve_table_name(),
                Key={"email": {"S": email}},
            )
            logger.info("Login attempt counter reset", email=email)
        except ClientError as exc:
            logger.error("DynamoDB delete_item failed", email=email, error=str(exc))

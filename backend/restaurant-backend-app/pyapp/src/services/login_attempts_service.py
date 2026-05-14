"""Service for tracking per-email failed login attempts and enforcing account lockout."""

import time

from commons.app_config import AppConfig
from commons.log_helper import logger
from repositories.login_attempts_repository import LoginAttemptsRepository


class LoginAttemptsService:
    """Tracks failed login attempts per email in DynamoDB and enforces account lockout.

    Each email maps to a single DynamoDB item with:
    - ``failed_attempts`` (Number): atomically incremented on each failure.
    - ``lockout_until`` (Number, Unix timestamp): set when the attempt ceiling is
      reached and doubles as the DynamoDB TTL so the item is auto-deleted after
      the lockout window expires.

    DynamoDB interaction is delegated to LoginAttemptsRepository; this class
    contains only the business logic (time comparisons, threshold checks).
    """

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise the service with lockout config and a login-attempts repository.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        self._max_attempts = cfg.max_login_attempts
        self._lockout_seconds = cfg.lockout_seconds
        self._repo = LoginAttemptsRepository(cfg)

    @property
    def max_attempts(self) -> int:
        """Return the maximum allowed failed attempts before lockout."""
        return self._max_attempts

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
        ts = self._repo.get_lockout_until(email)
        if ts is None:
            return None
        if ts > int(time.time()):
            return ts
        logger.info("Lockout expired, resetting attempt counter", email=email)
        self._repo.reset_attempts(email)
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
        new_count = self._repo.increment_failed_attempts(email)
        logger.info("Failed login attempt recorded", email=email, attempts=new_count)

        if new_count < self._max_attempts:
            return new_count, None

        lockout_until = int(time.time()) + self._lockout_seconds
        self._repo.set_lockout(email, lockout_until)
        logger.info("Account locked", email=email, lockout_until=lockout_until)
        return new_count, lockout_until

    def reset_attempts(self, email: str) -> None:
        """Delete the attempt record for the given email on successful login.

        Args:
            email: The user's email address used as the DynamoDB partition key.

        """
        self._repo.reset_attempts(email)
        logger.info("Login attempt counter reset", email=email)

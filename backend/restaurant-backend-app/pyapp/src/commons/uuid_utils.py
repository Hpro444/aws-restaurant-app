"""Shared UUID parsing helpers used across services and handlers."""

from __future__ import annotations

from uuid import UUID

from enums.http_status_code import HttpStatusCode

from commons.exceptions import ApplicationException
from commons.log_helper import logger


def coerce_uuid(
    value: UUID | str,
    *,
    error_code: int = HttpStatusCode.RESPONSE_UNAUTHORIZED,
    error_message: str = "Invalid authenticated identity",
    field_name: str | None = None,
) -> UUID:
    """Convert UUID-like input to UUID or raise ApplicationException.

    Args:
        value: UUID object or UUID string.
        error_code: HTTP status code to use on parse failure.
        error_message: Error payload message for parse failure.
        field_name: Optional field name for structured warning logs.

    Returns:
        Parsed UUID instance.

    Raises:
        ApplicationException: If value cannot be parsed as UUID.

    """
    if isinstance(value, UUID):
        return value

    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        if field_name:
            logger.warning("Invalid UUID for field", field=field_name, value=value)
        raise ApplicationException(error_code, error_message) from exc

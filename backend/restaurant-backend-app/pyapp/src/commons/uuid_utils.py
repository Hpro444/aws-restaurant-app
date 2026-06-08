"""Shared UUID parsing helpers used across services and handlers."""

from uuid import UUID

from enums import HttpStatusCode

from commons.exceptions import ApplicationException

_DEFAULT_UUID_ERROR_CODE = HttpStatusCode.RESPONSE_UNAUTHORIZED
_DEFAULT_UUID_ERROR_MESSAGE = "Invalid authenticated identity"


def parse_uuid_or_none(value: UUID | str) -> UUID | None:
    """Return UUID value or None when input cannot be parsed as UUID."""
    if isinstance(value, UUID):
        return value

    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None


def parse_uuid_or_raise(
    raw_value: UUID | str | None,
    *,
    code: int = _DEFAULT_UUID_ERROR_CODE,
    message: str = _DEFAULT_UUID_ERROR_MESSAGE,
    missing_message: str | None = None,
    invalid_message: str | None = None,
) -> UUID:
    """Return UUID value or raise ApplicationException with provided error details."""
    if missing_message is None:
        missing_message = message
    if invalid_message is None:
        invalid_message = message

    if isinstance(raw_value, UUID):
        return raw_value

    normalized_value = raw_value.strip() if isinstance(raw_value, str) else raw_value

    if normalized_value is None or normalized_value == "":
        raise ApplicationException(code, missing_message)

    try:
        return UUID(normalized_value)
    except (TypeError, ValueError):
        raise ApplicationException(code, invalid_message)


def coerce_uuid(
    value: UUID | str | None,
    *,
    code: int = _DEFAULT_UUID_ERROR_CODE,
    field_name: str | None = None,
    message: str | None = None,
) -> UUID:
    """Backward-compatible UUID coercion API used by service layer code."""
    resolved_message = message
    if resolved_message is None:
        if field_name:
            resolved_message = f"Invalid {field_name}"
        else:
            resolved_message = _DEFAULT_UUID_ERROR_MESSAGE
    return parse_uuid_or_raise(value, code=code, message=resolved_message)

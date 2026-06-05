"""Shared helpers for building standard API error payloads."""

from typing import Any


def auth_header_error_payload(message: str) -> dict[str, Any]:
    """Build auth-header error payload with field-level details."""
    content = validation_error_payload(
        "Authorization",
        message,
        "invalid_header",
    )
    content["message"] = message
    return content


def forbidden_role_error_payload(message: str) -> dict[str, Any]:
    """Build role-forbidden payload with field-level details."""
    content = validation_error_payload(
        "role",
        message,
        "forbidden_role",
    )
    content["message"] = message
    return content


def validation_error_payload(
    field: str,
    message: str,
    error_type: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build a single-field validation error payload.

    The optional ``error_type`` is included only when provided.
    """
    item: dict[str, Any] = {"field": field, "message": message}
    if error_type is not None:
        item["type"] = error_type
    return {"errors": [item]}


def _normalize_error_item(item: Any) -> dict[str, Any]:
    """Normalize one error item into a dict with at least ``message``."""
    if isinstance(item, dict):
        normalized: dict[str, Any] = {}
        for key in ("field", "message", "type", "code"):
            if key in item and item[key] is not None:
                normalized[key] = item[key]
        if "message" not in normalized:
            normalized["message"] = str(item)
        return normalized
    return {"message": str(item)}


def _extract_error_items(content: Any) -> list[dict[str, Any]]:
    """Extract and normalize a list of error objects from arbitrary content."""
    if isinstance(content, dict) and isinstance(content.get("errors"), list):
        raw_errors = content["errors"]
        if raw_errors:
            return [_normalize_error_item(item) for item in raw_errors]

    if isinstance(content, dict) and content.get("message") is not None:
        return [{"message": str(content["message"])}]

    if isinstance(content, list):
        return [_normalize_error_item(item) for item in content] or [
            {"message": "Request failed"}
        ]

    if isinstance(content, str):
        return [{"message": content}]

    return [{"message": str(content)}]


def _resolve_message(content: Any, errors: list[dict[str, Any]], default: str) -> str:
    """Resolve top-level message from payload, then fallback to first error."""
    if isinstance(content, dict) and content.get("message") is not None:
        return str(content["message"])

    first_error_message = next(
        (
            str(item.get("message"))
            for item in errors
            if isinstance(item.get("message"), str) and item.get("message")
        ),
        None,
    )
    return first_error_message or default


def normalize_error_content(
    content: Any = None,
    code: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Normalize raw error content to a status-based API contract.

    Contract:
    - 4xx always returns ``{"message": str, "errors": list}``.
    - 5xx returns ``{"message": str}``.
    - other statuses return ``{"message": str}``.
    """
    if content is None and "content" in kwargs:
        content = kwargs["content"]
    if code is None and "code" in kwargs:
        raw_code = kwargs["code"]
        code = raw_code if isinstance(raw_code, int) else None

    if code is None:
        if isinstance(content, str):
            return {"message": content}
        if isinstance(content, (dict, list)):
            return content
        return {"message": str(content)}

    if isinstance(content, str):
        return {"message": content}
    if 400 <= code < 500:
        errors = _extract_error_items(content)
        message = _resolve_message(content, errors, default="Request failed")
        return {"message": message, "errors": errors}

    if isinstance(content, dict) and content.get("message") is not None:
        return {"message": str(content["message"])}

    if isinstance(content, str):
        return {"message": content}

    if code >= 500:
        return {"message": "Internal server error"}

    return {"message": str(content)}

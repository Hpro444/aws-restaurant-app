"""Custom exception for propagating HTTP error responses through the Lambda call stack."""

from typing import Any


class ApplicationException(Exception):
    """Raised to signal an HTTP error response; carries the status code and body."""

    def __init__(self, code: int, content: Any) -> None:
        """Store the HTTP status code and response content."""
        self.code = code
        self.content = content

    def __str__(self) -> str:
        """Return a human-readable representation of the error."""
        return f"{self.code}:{self.content}"

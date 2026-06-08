"""Shared response-building utilities and HTTP status code constants."""

import json
from typing import Any, NoReturn

from enums import HttpStatusCode

from commons.exceptions import ApplicationException
from commons.response import LambdaResponse

__all__ = [
    "ApplicationException",
    "HttpStatusCode",
    "LambdaResponse",
    "build_response",
    "raise_error_response",
]


def build_response(
    content: Any, code: int = HttpStatusCode.RESPONSE_OK_CODE
) -> LambdaResponse:
    """Return a Lambda-compatible response for 2xx codes, or raise for errors.

    Args:
        content: Response body (any JSON-serialisable value).
        code: HTTP status code; any 2xx value returns normally, others raise.

    Returns:
        :class:`LambdaResponse` for successful responses.

    Raises:
        ApplicationException: For any non-2xx status code.

    """
    if HttpStatusCode.RESPONSE_OK_CODE <= code < 300:
        return LambdaResponse(statusCode=code, body=json.dumps(content))
    raise ApplicationException(code=code, content=content)


def raise_error_response(code: int, content: Any) -> NoReturn:
    """Raise an ApplicationException with the given code and content.

    Args:
        code: HTTP status code for the error.
        content: Error detail to include in the response body.

    Raises:
        ApplicationException: Always.

    """
    raise ApplicationException(code=code, content=content)

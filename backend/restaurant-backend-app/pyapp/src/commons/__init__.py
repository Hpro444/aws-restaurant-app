"""Shared response-building utilities and HTTP status code constants."""

import json

from commons.exceptions import ApplicationException

RESPONSE_OK_CODE = 200
RESPONSE_CREATED_CODE = 201
RESPONSE_BAD_REQUEST_CODE = 400
RESPONSE_UNAUTHORIZED = 401
RESPONSE_FORBIDDEN_CODE = 403
RESPONSE_RESOURCE_NOT_FOUND_CODE = 404
RESPONSE_CONFLICT_CODE = 409
RESPONSE_UNPROCESSABLE_ENTITY = 422
RESPONSE_INTERNAL_SERVER_ERROR = 500
RESPONSE_NOT_IMPLEMENTED = 501
RESPONSE_SERVICE_UNAVAILABLE_CODE = 503


def build_response(content, code=200):
    """Return a Lambda-compatible response dict for 2xx codes, or raise for errors.

    Args:
        content: Response body (any JSON-serialisable value).
        code: HTTP status code; any 2xx value returns normally, others raise.

    Returns:
        Dict with 'code' and 'body' keys for successful responses.

    Raises:
        ApplicationException: For any non-2xx status code.
    """
    if RESPONSE_OK_CODE <= code < 300:
        return {
            'statusCode': code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(content),
        }
    raise ApplicationException(code=code, content=content)


def raise_error_response(code, content):
    """Raise an ApplicationException with the given code and content.

    Args:
        code: HTTP status code for the error.
        content: Error detail to include in the response body.

    Raises:
        ApplicationException: Always.
    """
    raise ApplicationException(code=code, content=content)

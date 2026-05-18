"""JWT decoding utilities for extracting payload claims from access tokens."""

import jwt
from enums.http_status_code import HttpStatusCode

from commons.exceptions import ApplicationException


def decode_access_token_payload(access_token: str) -> dict:
    """Decode the JWT payload without signature verification.

    The token validity itself is verified by Cognito's get_user call before this
    helper is used.
    """
    try:
        # Decode without verification since Cognito's get_user already validated it
        return jwt.decode(access_token, options={"verify_signature": False})
    except Exception as exc:
        raise ApplicationException(
            code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
            content="Invalid or expired access token",
        ) from exc

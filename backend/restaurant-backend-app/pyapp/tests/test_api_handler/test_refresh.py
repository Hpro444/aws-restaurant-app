"""Tests for the POST /auth/refresh token refresh endpoint."""

from unittest.mock import MagicMock

from commons.exceptions import ApplicationException
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/auth/refresh"
_VALID_BODY = {"refresh_token": "mock-refresh-token"}


class TestRefresh(ApiHandlerLambdaTestCase):
    """Tests for the POST /auth/refresh token refresh flow."""

    def setUp(self) -> None:
        """Set up handler with a mocked Cognito service."""
        super().setUp()
        self.HANDLER._cognito_service.refresh_tokens = MagicMock(
            return_value="new-access-token"
        )

    def test_success_returns_200_with_new_access_token(self) -> None:
        """A valid refresh token should return 200 with a new access_token."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["access_token"], "new-access-token")

    def test_expired_refresh_token_returns_401(self) -> None:
        """An expired or invalid refresh token should return 401."""
        self.HANDLER._cognito_service.refresh_tokens = MagicMock(
            side_effect=ApplicationException(
                code=401, content="Invalid or expired refresh token"
            )
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["message"], "Invalid or expired refresh token")

    def test_missing_refresh_token_returns_422(self) -> None:
        """A request without a refresh_token field should return 422."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", {}), {})
        self.assertEqual(status(result), 422)

    def test_invalid_json_body_returns_422(self) -> None:
        """A non-JSON body should return 422."""
        event = {"path": _PATH, "httpMethod": "POST", "body": "not-json"}
        self.assertEqual(status(self.HANDLER.lambda_handler(event, {})), 422)

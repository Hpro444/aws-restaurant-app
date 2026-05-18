"""Tests for the POST /auth/sign-in authentication endpoint."""

from unittest.mock import MagicMock

from commons.exceptions import ApplicationException
from domain.auth_result import AuthResult
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/auth/sign-in"
_VALID_BODY = {
    "email": "jane@example.com",
    "password": "Secure123!",
}
_MOCK_AUTH_RESULT = AuthResult(
    access_token="mock-access-token",
    refresh_token="mock-refresh-token",
    username="Jane Doe",
    role="Customer",
)


class TestSignIn(ApiHandlerLambdaTestCase):
    """Tests for the POST /auth/sign-in authentication flow."""

    def setUp(self) -> None:
        """Set up handler with a mocked Cognito service."""
        super().setUp()
        self.HANDLER._cognito_service.authenticate_user = MagicMock(
            return_value=_MOCK_AUTH_RESULT
        )

    def test_success_returns_200_with_tokens_username_role(self) -> None:
        """Valid credentials should return 200 with access_token, refresh_token, username, and role."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["access_token"], "mock-access-token")
        self.assertEqual(body(result)["refresh_token"], "mock-refresh-token")
        self.assertEqual(body(result)["username"], "Jane Doe")
        self.assertEqual(body(result)["role"], "Customer")

    def test_invalid_credentials_returns_401(self) -> None:
        """Both wrong email and wrong password must return 401 with a generic message."""
        self.HANDLER._cognito_service.authenticate_user = MagicMock(
            side_effect=ApplicationException(code=401, content="Invalid credentials")
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 401)
        self.assertEqual(body(result), "Invalid credentials")

    def test_missing_email_returns_422(self) -> None:
        """A request without an email field should return 422."""
        incomplete = {k: v for k, v in _VALID_BODY.items() if k != "email"}
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(make_event(_PATH, "POST", incomplete), {})
            ),
            422,
        )

    def test_missing_password_returns_422(self) -> None:
        """A request without a password field should return 422."""
        incomplete = {k: v for k, v in _VALID_BODY.items() if k != "password"}
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(make_event(_PATH, "POST", incomplete), {})
            ),
            422,
        )

    def test_invalid_email_format_returns_422(self) -> None:
        """A malformed email should fail Pydantic validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", {**_VALID_BODY, "email": "not-an-email"}), {}
        )
        self.assertEqual(status(result), 422)

    def test_invalid_json_body_returns_422(self) -> None:
        """A non-JSON body should return 422."""
        event = {"path": _PATH, "httpMethod": "POST", "body": "not-json"}
        self.assertEqual(status(self.HANDLER.lambda_handler(event, {})), 422)

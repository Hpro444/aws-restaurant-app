"""Tests for the POST /auth/sign-up registration endpoint."""

from unittest.mock import MagicMock

from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/auth/sign-up"
_VALID_BODY = {
    "firstName": "Jane",
    "lastName": "Doe",
    "email": "jane@example.com",
    "password": "Secure123!",
}


class TestSignUp(ApiHandlerLambdaTestCase):
    """Tests for the POST /auth/sign-up registration flow."""

    def setUp(self) -> None:
        """Set up handler with a mocked Cognito service."""
        super().setUp()
        self.HANDLER._cognito_service.register_user = MagicMock(
            return_value="test-sub-123"
        )

    def test_success_returns_201_with_user_id(self) -> None:
        """A valid registration request should return 201 with userId and message."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 201)
        self.assertEqual(body(result)["user_id"], "test-sub-123")
        self.assertEqual(body(result)["message"], "User registered successfully")

    def test_missing_field_returns_422(self) -> None:
        """A request missing a required field should return 422."""
        incomplete = {k: v for k, v in _VALID_BODY.items() if k != "email"}
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(make_event(_PATH, "POST", incomplete), {})
            ),
            422,
        )

    def test_invalid_email_returns_422(self) -> None:
        """A request with a malformed email should return 422."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", {**_VALID_BODY, "email": "not-an-email"}), {}
        )
        self.assertEqual(status(result), 422)

    def test_short_password_returns_422(self) -> None:
        """A password shorter than 8 characters should return 422."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", {**_VALID_BODY, "password": "short"}), {}
        )
        self.assertEqual(status(result), 422)

    def test_invalid_json_body_returns_422(self) -> None:
        """A non-JSON body should return 422."""
        event = {"path": _PATH, "httpMethod": "POST", "body": "not-json"}
        self.assertEqual(status(self.HANDLER.lambda_handler(event, {})), 422)

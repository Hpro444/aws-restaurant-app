"""Tests for routing and the POST /auth/sign-up endpoint."""

import json
from unittest.mock import MagicMock

from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase


def _make_event(path: str, method: str, body: dict) -> dict:
    """Build a minimal API Gateway-style Lambda event."""
    return {"path": path, "httpMethod": method, "body": json.dumps(body)}


def _status(result: dict) -> int:
    """Extract the HTTP status code from a Lambda proxy response."""
    return result["statusCode"]


def _body(result: dict) -> dict:
    """Parse and return the response body dict from a Lambda proxy response."""
    return json.loads(result["body"])


_SIGN_UP_PATH = "/auth/sign-up"
_VALID_BODY = {
    "firstName": "Jane",
    "lastName": "Doe",
    "email": "jane@example.com",
    "password": "Secure123!",
}


class TestRouting(ApiHandlerLambdaTestCase):
    """Tests that handle_request dispatches correctly by path and method."""

    def test_unknown_path_returns_404(self) -> None:
        """An unrecognised path should return 404."""
        event = _make_event("/unknown", "POST", {})
        self.assertEqual(_status(self.HANDLER.lambda_handler(event, {})), 404)

    def test_wrong_method_returns_404(self) -> None:
        """A GET to the sign-up path should return 404."""
        event = _make_event(_SIGN_UP_PATH, "GET", _VALID_BODY)
        self.assertEqual(_status(self.HANDLER.lambda_handler(event, {})), 404)


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
        result = self.HANDLER.lambda_handler(
            _make_event(_SIGN_UP_PATH, "POST", _VALID_BODY), {}
        )
        self.assertEqual(_status(result), 201)
        self.assertEqual(_body(result)["userId"], "test-sub-123")
        self.assertEqual(_body(result)["message"], "User registered successfully")

    def test_missing_field_returns_422(self) -> None:
        """A request missing a required field should return 422."""
        body = {k: v for k, v in _VALID_BODY.items() if k != "email"}
        result = self.HANDLER.lambda_handler(
            _make_event(_SIGN_UP_PATH, "POST", body), {}
        )
        self.assertEqual(_status(result), 422)

    def test_invalid_email_returns_422(self) -> None:
        """A request with a malformed email should return 422."""
        result = self.HANDLER.lambda_handler(
            _make_event(
                _SIGN_UP_PATH, "POST", {**_VALID_BODY, "email": "not-an-email"}
            ),
            {},
        )
        self.assertEqual(_status(result), 422)

    def test_short_password_returns_422(self) -> None:
        """A password shorter than 8 characters should return 422."""
        result = self.HANDLER.lambda_handler(
            _make_event(_SIGN_UP_PATH, "POST", {**_VALID_BODY, "password": "short"}), {}
        )
        self.assertEqual(_status(result), 422)

    def test_invalid_json_body_returns_422(self) -> None:
        """A non-JSON body should return 422."""
        event = {"path": _SIGN_UP_PATH, "httpMethod": "POST", "body": "not-json"}
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(_status(result), 422)

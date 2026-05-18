"""Base test case setup for the api-handler Lambda."""

import importlib
import json
import unittest
from unittest.mock import MagicMock

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module("lambdas.api-handler.handler")  # type: ignore[import-untyped]


class ApiHandlerLambdaTestCase(unittest.TestCase):
    """Common setup for api-handler Lambda test cases."""

    def setUp(self) -> None:
        """Instantiate ApiHandler without constructor side effects and inject test doubles."""
        # Keep a real CognitoService instance (without __init__) so tests that
        # exercise authenticate_user lockout logic still run real service code.
        self.mock_cognito_service = LAMBDA_HANDLER.CognitoService.__new__(
            LAMBDA_HANDLER.CognitoService
        )
        self.mock_cognito_service._settings = MagicMock()
        self.mock_cognito_service._pool_id = "mock-pool-id"
        self.mock_cognito_service._client_id = "mock-client-id"
        self.mock_cognito_service._client = MagicMock()
        self.mock_cognito_service._login_attempts_service = MagicMock()
        self.mock_cognito_service._login_attempts_service.max_attempts = 5

        self.mock_table_availability_service = MagicMock()
        self.mock_registration_service = MagicMock()
        self.mock_user_profile_service = MagicMock()

        self.HANDLER = LAMBDA_HANDLER.ApiHandler.__new__(LAMBDA_HANDLER.ApiHandler)
        self.HANDLER._cognito_service = self.mock_cognito_service
        self.HANDLER._registration_service = self.mock_registration_service
        self.HANDLER._table_availability_service = self.mock_table_availability_service
        self.HANDLER._user_profile_service = self.mock_user_profile_service


def make_event(
    path: str,
    method: str,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    """Build a minimal API Gateway-style Lambda event."""
    event = {"path": path, "httpMethod": method}
    if body is not None:
        event["body"] = json.dumps(body)
    if headers is not None:
        event["headers"] = headers
    return event


def make_get_event(path: str, params: dict | None) -> dict:
    """Build a minimal API Gateway-style Lambda GET event with query string parameters."""
    return {"path": path, "httpMethod": "GET", "queryStringParameters": params}


def status(result: dict) -> int:
    """Extract the HTTP status code from a Lambda proxy response."""
    return result["statusCode"]


def body(result: dict) -> dict:
    """Parse and return the response body dict from a Lambda proxy response."""
    return json.loads(result["body"])

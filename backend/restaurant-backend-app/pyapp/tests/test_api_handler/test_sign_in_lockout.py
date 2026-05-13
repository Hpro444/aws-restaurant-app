"""Tests for the account-lockout behaviour inside CognitoService.authenticate_user."""

import time
from unittest.mock import MagicMock

from botocore.exceptions import ClientError
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/auth/sign-in"
_VALID_BODY = {"email": "jane@example.com", "password": "Secure123!"}
_FUTURE_TS = int(time.time()) + 900

_MOCK_INITIATE_AUTH_RESP = {
    "AuthenticationResult": {
        "AccessToken": "mock-access-token",
        "RefreshToken": "mock-refresh-token",
    }
}
_MOCK_GET_USER_RESP = {
    "UserAttributes": [
        {"Name": "custom:first_name", "Value": "Jane"},
        {"Name": "custom:last_name", "Value": "Doe"},
    ]
}
_MOCK_GROUPS_RESP = {"Groups": [{"GroupName": "User"}]}

_NOT_AUTHORIZED = ClientError(
    {
        "Error": {
            "Code": "NotAuthorizedException",
            "Message": "Incorrect username or password.",
        }
    },
    "InitiateAuth",
)


class TestSignInLockout(ApiHandlerLambdaTestCase):
    """Tests for failed-attempt tracking and account-lockout logic inside CognitoService."""

    def setUp(self) -> None:
        """Configure mocks on the cognito service's internals for isolation."""
        super().setUp()
        cognito = self.HANDLER._cognito_service

        # Skip pool/client resolution
        cognito._pool_id = "us-east-1_mockpool"
        cognito._client_id = "mock-client-id"

        # Default: Cognito auth succeeds
        cognito._client.initiate_auth = MagicMock(return_value=_MOCK_INITIATE_AUTH_RESP)
        cognito._client.admin_get_user = MagicMock(return_value=_MOCK_GET_USER_RESP)
        cognito._client.admin_list_groups_for_user = MagicMock(
            return_value=_MOCK_GROUPS_RESP
        )

        # Default: account not locked, no prior failures
        cognito._login_attempts_service.get_lockout_until = MagicMock(return_value=None)
        cognito._login_attempts_service.increment_failed_attempts = MagicMock(
            return_value=(1, None)
        )
        cognito._login_attempts_service.reset_attempts = MagicMock()

    def test_locked_account_returns_423_before_cognito_is_called(self) -> None:
        """A locked account must be rejected immediately without calling initiate_auth."""
        self.HANDLER._cognito_service._login_attempts_service.get_lockout_until = (
            MagicMock(return_value=_FUTURE_TS)
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 423)
        self.assertEqual(body(result)["lockout_until"], _FUTURE_TS)
        self.HANDLER._cognito_service._client.initiate_auth.assert_not_called()

    def test_early_failures_return_plain_401(self) -> None:
        """Failures 1–3 must return plain 401 with no extra fields."""
        self.HANDLER._cognito_service._client.initiate_auth = MagicMock(
            side_effect=_NOT_AUTHORIZED
        )
        self.HANDLER._cognito_service._login_attempts_service.increment_failed_attempts = MagicMock(
            return_value=(2, None)
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 401)
        self.assertNotIn("remaining_attempts", body(result))

    def test_4th_failure_includes_remaining_attempts(self) -> None:
        """The 4th failed attempt must return 401 with remaining_attempts equal to 1."""
        self.HANDLER._cognito_service._client.initiate_auth = MagicMock(
            side_effect=_NOT_AUTHORIZED
        )
        self.HANDLER._cognito_service._login_attempts_service.increment_failed_attempts = MagicMock(
            return_value=(4, None)
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["remaining_attempts"], 1)

    def test_5th_failure_locks_account_and_returns_423(self) -> None:
        """The 5th failed attempt must lock the account and return 423 with lockout_until."""
        self.HANDLER._cognito_service._client.initiate_auth = MagicMock(
            side_effect=_NOT_AUTHORIZED
        )
        self.HANDLER._cognito_service._login_attempts_service.increment_failed_attempts = MagicMock(
            return_value=(5, _FUTURE_TS)
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 423)
        self.assertEqual(body(result)["lockout_until"], _FUTURE_TS)

    def test_success_resets_attempt_counter(self) -> None:
        """A successful login must call reset_attempts exactly once."""
        self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.HANDLER._cognito_service._login_attempts_service.reset_attempts.assert_called_once_with(
            "jane@example.com"
        )

    def test_expired_lockout_resets_counter_and_allows_attempt(self) -> None:
        """An expired lockout_until must delete the item and let the attempt through as a fresh failure."""
        reset_mock = MagicMock()
        self.HANDLER._cognito_service._login_attempts_service.get_lockout_until = (
            MagicMock(return_value=None)
        )
        self.HANDLER._cognito_service._login_attempts_service.reset_attempts = (
            reset_mock
        )
        self.HANDLER._cognito_service._client.initiate_auth = MagicMock(
            side_effect=_NOT_AUTHORIZED
        )
        self.HANDLER._cognito_service._login_attempts_service.increment_failed_attempts = MagicMock(
            return_value=(1, None)
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 401)
        self.assertNotIn("remaining_attempts", body(result))

    def test_non_auth_cognito_error_bypasses_lockout_logic(self) -> None:
        """A 500-class Cognito error must propagate as-is without touching the attempt counter."""
        self.HANDLER._cognito_service._client.initiate_auth = MagicMock(
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "InternalErrorException",
                        "Message": "Service error",
                    }
                },
                "InitiateAuth",
            )
        )
        result = self.HANDLER.lambda_handler(make_event(_PATH, "POST", _VALID_BODY), {})
        self.assertEqual(status(result), 500)
        self.HANDLER._cognito_service._login_attempts_service.increment_failed_attempts.assert_not_called()

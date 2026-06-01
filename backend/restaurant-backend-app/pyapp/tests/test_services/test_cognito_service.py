"""Tests for CognitoService.register_user — sub extraction and Cognito API calls."""

import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException
    from enums.user_role import UserRole
    from services.cognito_service import CognitoService

_SUB = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_POOL_ID = "us-east-1_TestPool"
_EMAIL = "jane@example.com"
_FIRST_NAME = "Jane"
_LAST_NAME = "Doe"
_PASSWORD = "Secure123!"

_ADMIN_CREATE_USER_RESPONSE = {
    "User": {
        "UserStatus": "FORCE_CHANGE_PASSWORD",
        "Attributes": [
            {"Name": "sub", "Value": _SUB},
            {"Name": "email", "Value": _EMAIL},
        ],
    }
}


def _client_error(code: str) -> ClientError:
    """Build a minimal ClientError with the given error Code."""
    return ClientError(
        {"Error": {"Code": code, "Message": code}},
        "operation",
    )


class _CognitoServiceTestCase(unittest.TestCase):
    """Base: patches boto3 and pre-wires the Cognito mock client for register_user tests."""

    def setUp(self) -> None:
        """Patch boto3, resolve pool/client IDs, and stub the happy-path Cognito calls."""
        patcher = patch("services.cognito_service.boto3")
        self.mock_boto3 = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client

        # Pre-resolve pool ID so _resolve_pool_id() returns without calling list_user_pools.
        self.service = CognitoService()
        self.service._pool_id = _POOL_ID

        self.mock_client.admin_create_user.return_value = _ADMIN_CREATE_USER_RESPONSE
        self.mock_client.admin_set_user_password.return_value = {}
        self.mock_client.admin_add_user_to_group.return_value = {}


class TestRegisterUserReturnValue(_CognitoServiceTestCase):
    """Tests that register_user returns the Cognito sub extracted from the response."""

    def test_returns_cognito_sub(self) -> None:
        """The return value must equal the sub attribute in the admin_create_user response."""
        from pydantic import SecretStr

        result = self.service.register_user(
            first_name=_FIRST_NAME,
            last_name=_LAST_NAME,
            email=_EMAIL,
            password=SecretStr(_PASSWORD),
        )

        self.assertEqual(result, _SUB)


class TestRegisterUserCognitoCalls(_CognitoServiceTestCase):
    """Tests that register_user makes the correct Cognito API calls."""

    def setUp(self) -> None:
        """Set up service and import SecretStr for all call tests."""
        super().setUp()
        from pydantic import SecretStr

        self._secret = SecretStr(_PASSWORD)

    def test_creates_user_with_correct_attributes(self) -> None:
        """admin_create_user must be called with all required UserAttributes."""
        self.service.register_user(
            first_name=_FIRST_NAME,
            last_name=_LAST_NAME,
            email=_EMAIL,
            password=self._secret,
        )

        call_kwargs = self.mock_client.admin_create_user.call_args.kwargs
        attrs = {a["Name"]: a["Value"] for a in call_kwargs["UserAttributes"]}
        self.assertEqual(attrs["email"], _EMAIL)
        self.assertEqual(attrs["email_verified"], "true")
        self.assertEqual(attrs["custom:first_name"], _FIRST_NAME)
        self.assertEqual(attrs["custom:last_name"], _LAST_NAME)

    def test_sets_password_permanently(self) -> None:
        """admin_set_user_password must be called with Permanent=True."""
        self.service.register_user(
            first_name=_FIRST_NAME,
            last_name=_LAST_NAME,
            email=_EMAIL,
            password=self._secret,
        )

        call_kwargs = self.mock_client.admin_set_user_password.call_args.kwargs
        self.assertTrue(call_kwargs["Permanent"])
        self.assertEqual(call_kwargs["Password"], _PASSWORD)

    def test_adds_user_to_correct_group(self) -> None:
        """admin_add_user_to_group must be called with the resolved role as GroupName."""
        self.service.register_user(
            first_name=_FIRST_NAME,
            last_name=_LAST_NAME,
            email=_EMAIL,
            password=self._secret,
            role=UserRole.WAITER,
        )

        call_kwargs = self.mock_client.admin_add_user_to_group.call_args.kwargs
        self.assertEqual(call_kwargs["GroupName"], UserRole.WAITER)

    def test_defaults_to_customer_role(self) -> None:
        """When no role is specified, the user must be added to the Customer group."""
        self.service.register_user(
            first_name=_FIRST_NAME,
            last_name=_LAST_NAME,
            email=_EMAIL,
            password=self._secret,
        )

        call_kwargs = self.mock_client.admin_add_user_to_group.call_args.kwargs
        self.assertEqual(call_kwargs["GroupName"], UserRole.CUSTOMER)


class TestRegisterUserErrorHandling(_CognitoServiceTestCase):
    """Tests that Cognito errors are mapped to the correct ApplicationException codes."""

    def test_raises_409_on_existing_email(self) -> None:
        """UsernameExistsException must surface as ApplicationException with code 409."""
        from pydantic import SecretStr

        self.mock_client.admin_create_user.side_effect = _client_error(
            "UsernameExistsException"
        )

        with self.assertRaises(ApplicationException) as ctx:
            self.service.register_user(
                first_name=_FIRST_NAME,
                last_name=_LAST_NAME,
                email=_EMAIL,
                password=SecretStr(_PASSWORD),
            )

        self.assertEqual(ctx.exception.code, 409)

    def test_raises_500_on_unexpected_cognito_error(self) -> None:
        """Any non-UsernameExistsException ClientError must surface as ApplicationException(500)."""
        from pydantic import SecretStr

        self.mock_client.admin_create_user.side_effect = _client_error("InternalError")

        with self.assertRaises(ApplicationException) as ctx:
            self.service.register_user(
                first_name=_FIRST_NAME,
                last_name=_LAST_NAME,
                email=_EMAIL,
                password=SecretStr(_PASSWORD),
            )

        self.assertEqual(ctx.exception.code, 500)

    def test_raises_500_when_set_password_fails(self) -> None:
        """A ClientError from admin_set_user_password must surface as ApplicationException(500)."""
        from pydantic import SecretStr

        self.mock_client.admin_set_user_password.side_effect = _client_error(
            "InternalError"
        )

        with self.assertRaises(ApplicationException) as ctx:
            self.service.register_user(
                first_name=_FIRST_NAME,
                last_name=_LAST_NAME,
                email=_EMAIL,
                password=SecretStr(_PASSWORD),
            )

        self.assertEqual(ctx.exception.code, 500)

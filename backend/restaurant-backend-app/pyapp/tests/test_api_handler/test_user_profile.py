"""Tests for the GET and PUT /users/profile endpoints."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from domain.admin import Admin
from domain.user import Customer, Waiter
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/users/profile"
_VALID_TOKEN = "Bearer valid-token"
_HEADERS = {"Authorization": _VALID_TOKEN}


class TestUserProfile(ApiHandlerLambdaTestCase):
    """Tests for the GET /users/profile endpoint."""

    def setUp(self) -> None:
        """Create handler instance and sample customer/waiter/admin fixtures."""
        super().setUp()
        self.mock_customer = Customer(
            id=uuid4(),
            fname="Jane",
            lname="Doe",
            email="jane@example.com",
            image_url="",
        )
        self.mock_waiter = Waiter(
            id=uuid4(),
            fname="John",
            lname="Smith",
            email="john@example.com",
            image_url="",
            location_id=uuid4(),
        )
        self.mock_admin = Admin(
            id=uuid4(),
            fname="Alice",
            lname="Admin",
            email="alice@example.com",
            image_url="",
        )

    def test_customer_profile_success(self):
        """Return 200 and customer payload when token resolves to customer role."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(self.mock_customer.id), UserRole.CUSTOMER.value)
        )
        self.HANDLER._user_profile_service.get_user_profile = MagicMock(
            return_value=self.mock_customer
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["email"], self.mock_customer.email)
        self.assertEqual(body(result)["role"], UserRole.CUSTOMER.value)

    def test_waiter_profile_success(self):
        """Return 200 and waiter payload when token resolves to waiter role."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(self.mock_waiter.id), UserRole.WAITER.value)
        )
        self.HANDLER._user_profile_service.get_user_profile = MagicMock(
            return_value=self.mock_waiter
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["email"], self.mock_waiter.email)
        self.assertEqual(body(result)["role"], UserRole.WAITER.value)

    def test_invalid_token_returns_401(self):
        """Return 401 when access token validation fails."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401, content="Invalid or expired access token"
            )
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 401)
        self.assertEqual(body(result), "Invalid or expired access token")

    def test_profile_not_found_returns_404(self):
        """Return 404 when profile lookup returns no user record."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(self.mock_customer.id), UserRole.CUSTOMER.value)
        )
        self.HANDLER._user_profile_service.get_user_profile = MagicMock(
            side_effect=ApplicationException(code=404, content="Profile not found")
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 404)
        self.assertEqual(body(result), "Profile not found")

    def test_admin_profile_success(self):
        """Return 200 and admin payload when token resolves to admin role."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(self.mock_admin.id), UserRole.ADMIN.value)
        )
        self.HANDLER._user_profile_service.get_user_profile = MagicMock(
            return_value=self.mock_admin
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["email"], self.mock_admin.email)
        self.assertEqual(body(result)["role"], UserRole.ADMIN.value)

    def test_unsupported_role_returns_403(self):
        """Return 403 when token contains a role unsupported by profile endpoint."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), "Visitor")
        )
        self.HANDLER._user_profile_service.get_user_profile = MagicMock(
            side_effect=ApplicationException(
                code=403, content="Role is not supported for this endpoint"
            )
        )
        event = make_event(_PATH, "GET", headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 403)
        self.assertIn("Role is not supported", body(result))


_UPDATE_BODY = {
    "first_name": "NewFirst",
    "last_name": "NewLast",
    "image_url": "https://example.com/pic.jpg",
}


class TestUpdateUserProfile(ApiHandlerLambdaTestCase):
    """Tests for the PUT /users/profile endpoint."""

    def setUp(self) -> None:
        """Create handler instance and sample customer fixture."""
        super().setUp()
        self.mock_customer = Customer(
            id=uuid4(),
            fname="NewFirst",
            lname="NewLast",
            email="jane@example.com",
            image_url="https://example.com/pic.jpg",
        )

    def test_update_customer_success(self):
        """Return 200 with updated fields when PUT succeeds for a customer."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(self.mock_customer.id), UserRole.CUSTOMER.value)
        )
        self.HANDLER._user_profile_service.update_user_profile = MagicMock(
            return_value=self.mock_customer
        )
        event = make_event(_PATH, "PUT", body=_UPDATE_BODY, headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["first_name"], "NewFirst")
        self.assertEqual(body(result)["last_name"], "NewLast")
        self.assertEqual(body(result)["role"], UserRole.CUSTOMER.value)

    def test_update_missing_field_returns_422(self):
        """Return 422 when a required field is absent from the PUT body."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.CUSTOMER.value)
        )
        event = make_event(_PATH, "PUT", body={"last_name": "X"}, headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 422)

    def test_update_invalid_token_returns_401(self):
        """Return 401 when the access token is invalid."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401, content="Invalid or expired access token"
            )
        )
        event = make_event(_PATH, "PUT", body=_UPDATE_BODY, headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 401)

    def test_update_profile_not_found_returns_404(self):
        """Return 404 when the service cannot find the profile to update."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.CUSTOMER.value)
        )
        self.HANDLER._user_profile_service.update_user_profile = MagicMock(
            side_effect=ApplicationException(code=404, content="Profile not found")
        )
        event = make_event(_PATH, "PUT", body=_UPDATE_BODY, headers=_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})
        self.assertEqual(status(result), 404)

"""Unit tests for UserProfileService."""

from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException
    from domain.user import Customer, Waiter
    from enums.http_status_code import HttpStatusCode
    from enums.user_role import UserRole
    from services.user_profile_service import UserProfileService


class TestUserProfileService(TestCase):
    """Unit tests that verify UserProfileService correctly retrieves user profiles based on access tokens, including error handling for missing profiles and unsupported roles."""

    def setUp(self):
        """Create service with mocked dependencies and sample domain entities."""
        self.mock_cognito = MagicMock()
        self.mock_customer_repo = MagicMock()
        self.mock_waiter_repo = MagicMock()
        self.service = UserProfileService(
            cognito_service=self.mock_cognito,
            customer_repository=self.mock_customer_repo,
            waiter_repository=self.mock_waiter_repo,
        )
        self.customer = Customer(
            id=uuid4(),
            fname="Jane",
            lname="Doe",
            email="jane@example.com",
            image_url="",
        )
        self.waiter = Waiter(
            id=uuid4(),
            fname="John",
            lname="Smith",
            email="john@example.com",
            image_url="",
            restaurant_id=uuid4(),
        )

    def test_get_customer_profile_success(self):
        """Return customer profile when token resolves to a customer identity."""
        self.mock_cognito.get_identity_from_access_token.return_value = (
            str(self.customer.id),
            UserRole.CUSTOMER.value,
        )
        self.mock_customer_repo.get.return_value = self.customer
        result = self.service.get_user_profile("valid-token")
        self.assertEqual(result.email, self.customer.email)

    def test_get_waiter_profile_success(self):
        """Return waiter profile when token resolves to a waiter identity."""
        self.mock_cognito.get_identity_from_access_token.return_value = (
            str(self.waiter.id),
            UserRole.WAITER.value,
        )
        self.mock_waiter_repo.get.return_value = self.waiter
        result = self.service.get_user_profile("valid-token")
        self.assertEqual(result.email, self.waiter.email)

    def test_profile_not_found_raises_404(self):
        """Raise 404 when the role-specific repository has no matching profile."""
        self.mock_cognito.get_identity_from_access_token.return_value = (
            str(self.customer.id),
            UserRole.CUSTOMER.value,
        )
        self.mock_customer_repo.get.return_value = None
        with self.assertRaises(ApplicationException) as ctx:
            self.service.get_user_profile("valid-token")
        self.assertEqual(
            ctx.exception.code, HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE
        )
        self.assertIn("Profile not found", str(ctx.exception.content))

    def test_unsupported_role_raises_403(self):
        """Raise 403 when the token role is not supported by the endpoint."""
        self.mock_cognito.get_identity_from_access_token.return_value = (
            str(uuid4()),
            "Admin",
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.get_user_profile("valid-token")
        self.assertEqual(ctx.exception.code, HttpStatusCode.RESPONSE_FORBIDDEN_CODE)
        self.assertIn("Role is not supported", str(ctx.exception.content))

    def test_invalid_token_raises_401(self):
        """Propagate 401 when token validation fails in Cognito service."""
        self.mock_cognito.get_identity_from_access_token.side_effect = (
            ApplicationException(code=401, content="Invalid or expired access token")
        )
        with self.assertRaises(ApplicationException) as ctx:
            self.service.get_user_profile("invalid-token")
        self.assertEqual(ctx.exception.code, 401)
        self.assertIn("Invalid or expired access token", str(ctx.exception.content))

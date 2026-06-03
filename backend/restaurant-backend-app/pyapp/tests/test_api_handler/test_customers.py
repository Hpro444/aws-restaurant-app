"""Tests for the GET /customers endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.customers import CustomerResponse
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/customers"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


class TestCustomers(ApiHandlerLambdaTestCase):
    """Tests for GET /customers waiter-protected endpoint."""

    def setUp(self) -> None:
        """Set default waiter identity and service mock responses."""
        super().setUp()
        self.waiter_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.waiter_id, UserRole.WAITER)
        )
        self.HANDLER._customers_service.get_customers = MagicMock(
            return_value=[
                CustomerResponse(
                    id=uuid4(), user_name="Jane Doe", email="jane@example.com"
                ),
                CustomerResponse(
                    id=uuid4(), user_name="John Smith", email="john@example.com"
                ),
            ]
        )

    def test_get_customers_returns_200_and_customer_list(self) -> None:
        """Waiter gets a 200 response with the customer list payload."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["user_name"], "Jane Doe")
        self.assertEqual(payload[0]["email"], "jane@example.com")
        self.HANDLER._customers_service.get_customers.assert_called_once()

    def test_get_customers_returns_200_and_empty_list(self) -> None:
        """Waiter receives an empty list when no customers exist."""
        self.HANDLER._customers_service.get_customers = MagicMock(return_value=[])

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])

    def test_missing_authorization_header_returns_401(self) -> None:
        """Missing Authorization header should return 401."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})
        self.assertEqual(status(result), 401)
        self.HANDLER._customers_service.get_customers.assert_not_called()

    def test_invalid_token_returns_401(self) -> None:
        """Invalid token should return 401 and not call customer service."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401,
                content="Invalid or expired access token",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["message"], "Invalid or expired access token")
        self.HANDLER._customers_service.get_customers.assert_not_called()

    def test_non_waiter_role_returns_403(self) -> None:
        """Only waiter role is allowed to access GET /customers."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.CUSTOMER)
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"], "Only waiters can access customers list."
        )
        self.HANDLER._customers_service.get_customers.assert_not_called()

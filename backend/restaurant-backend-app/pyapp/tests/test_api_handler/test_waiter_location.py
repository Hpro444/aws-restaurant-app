"""Tests for the GET /users/waiter/location endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.locations import LocationAddressResponse
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/users/waiter/location"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


class TestWaiterLocation(ApiHandlerLambdaTestCase):
    """Tests for waiter-assigned location endpoint."""

    def setUp(self) -> None:
        """Set default mocked service response for waiter location."""
        super().setUp()
        self.location_id = str(uuid4())
        self.HANDLER._user_profile_service.get_waiter_location = MagicMock(
            return_value=LocationAddressResponse(
                location_id=self.location_id,
                location_address="48 Rustaveli Avenue",
            )
        )

    def test_waiter_location_success_returns_200(self) -> None:
        """Authenticated waiter gets assigned location id and address."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["location_id"], self.location_id)
        self.assertEqual(body(result)["location_address"], "48 Rustaveli Avenue")
        self.HANDLER._user_profile_service.get_waiter_location.assert_called_once_with(
            "valid-token"
        )

    def test_missing_authorization_header_returns_401(self) -> None:
        """Missing Authorization header should return 401."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._user_profile_service.get_waiter_location.assert_not_called()

    def test_non_waiter_role_returns_403(self) -> None:
        """Only waiter role is allowed to access GET /users/waiter/location."""
        self.HANDLER._user_profile_service.get_waiter_location = MagicMock(
            side_effect=ApplicationException(
                code=403,
                content="Only waiters can access this endpoint",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"], "Only waiters can access this endpoint"
        )

    def test_location_not_found_returns_404(self) -> None:
        """Return 404 when waiter has no existing location row."""
        self.HANDLER._user_profile_service.get_waiter_location = MagicMock(
            side_effect=ApplicationException(
                code=404,
                content="Waiter location not found",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Waiter location not found")

    def test_invalid_token_returns_401(self) -> None:
        """Invalid token should return 401 and not query waiter location service."""
        self.HANDLER._user_profile_service.get_waiter_location = MagicMock(
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

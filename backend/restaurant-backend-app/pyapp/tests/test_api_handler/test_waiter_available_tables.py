"""Tests for the GET /bookings/waiter/tables availability endpoint."""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import UUID

from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    status,
)

_PATH = "/bookings/waiter/tables"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()
_VALID_PARAMS = {
    "location_id": "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3",
    "date": _TOMORROW,
    "guests_number": "4",
    "from_time": f"{_TOMORROW}T12:00:00Z",
    "to_time": f"{_TOMORROW}T16:00:00Z",
}
_MOCK_RESPONSE_DATA = {
    "tables": [
        {
            "table_id": "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3",
            "table_number": 1,
            "capacity": 4,
            "location_address": "48 Rustaveli Avenue, Tbilisi",
            "available_slots": [
                {
                    "slot_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "start_time": f"{_TOMORROW}T12:00:00+00:00",
                    "end_time": f"{_TOMORROW}T13:30:00+00:00",
                }
            ],
        }
    ]
}


def _event(params: dict | None, headers: dict | None = _VALID_HEADERS) -> dict:
    """Build a GET event with query parameters and optional headers."""
    event = {"path": _PATH, "httpMethod": "GET", "queryStringParameters": params}
    if headers is not None:
        event["headers"] = headers
    return event


class TestWaiterAvailableTables(ApiHandlerLambdaTestCase):
    """Tests for the waiter-facing table availability flow."""

    def setUp(self) -> None:
        """Set up handler with waiter auth and a mocked availability service."""
        super().setUp()
        self.waiter_id = str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.waiter_id, UserRole.WAITER)
        )
        mock_response = MagicMock()
        mock_response.model_dump.return_value = _MOCK_RESPONSE_DATA
        self.HANDLER._table_availability_service.get_available_tables_for_waiter = (
            MagicMock(return_value=mock_response)
        )

    def test_success_returns_200_with_tables(self) -> None:
        """A valid waiter request returns the available tables payload."""
        result = self.HANDLER.lambda_handler(
            _event(_VALID_PARAMS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertIn("tables", body(result))
        self.assertEqual(
            body(result)["tables"][0]["location_address"],
            "48 Rustaveli Avenue, Tbilisi",
        )
        self.HANDLER._table_availability_service.get_available_tables_for_waiter.assert_called_once_with(
            location_id=UUID(_VALID_PARAMS["location_id"]),
            booking_date=_TOMORROW,
            guests_number=4,
            from_time=f"{_TOMORROW}T12:00:00Z",
            to_time=f"{_TOMORROW}T16:00:00Z",
        )

    def test_non_waiter_returns_403(self) -> None:
        """Only waiters can access the waiter tables endpoint."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(UUID(int=1)), UserRole.CUSTOMER)
        )

        result = self.HANDLER.lambda_handler(
            _event(_VALID_PARAMS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.HANDLER._table_availability_service.get_available_tables_for_waiter.assert_not_called()

    def test_missing_from_time_returns_422(self) -> None:
        """from_time is required for waiter availability filtering."""
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "from_time"}
        result = self.HANDLER.lambda_handler(
            _event(params),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables_for_waiter.assert_not_called()

    def test_invalid_time_order_returns_422(self) -> None:
        """from_time must be earlier than to_time."""
        result = self.HANDLER.lambda_handler(
            _event(
                {
                    **_VALID_PARAMS,
                    "from_time": f"{_TOMORROW}T16:00:00Z",
                    "to_time": f"{_TOMORROW}T12:00:00Z",
                }
            ),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables_for_waiter.assert_not_called()

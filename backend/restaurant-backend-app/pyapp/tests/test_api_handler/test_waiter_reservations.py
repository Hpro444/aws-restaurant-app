"""Tests for the GET /reservations/waiter endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.waiter_reservations import (
    WaiterReservationListResponse,
    WaiterReservationView,
)
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    status,
)

_PATH = "/reservations/waiter"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}
_VALID_PARAMS = {"date": "2026-05-16", "time_from": "12:00", "table_name": "5"}
_RESERVATION_ID = str(uuid4())


def _event(params: dict | None, headers: dict | None = _VALID_HEADERS) -> dict:
    """Build a GET event with both query parameters and headers."""
    event = {"path": _PATH, "httpMethod": "GET", "queryStringParameters": params}
    if headers is not None:
        event["headers"] = headers
    return event


def _view() -> WaiterReservationView:
    """Build a representative waiter table-view reservation."""
    return WaiterReservationView(
        reservation_id=_RESERVATION_ID,
        customer_id=str(uuid4()),
        location_address="1 Freedom Square, Tbilisi",
        table_number=5,
        date="2026-05-16",
        time_from="12:00",
        time_to="13:30",
        guests_number=4,
    )


class TestGetWaiterReservations(ApiHandlerLambdaTestCase):
    """Covers auth gating, validation, and the response shape."""

    def setUp(self) -> None:
        """Default to an authenticated waiter and a one-item service response."""
        super().setUp()
        self.waiter_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.waiter_id, UserRole.WAITER)
        )
        self.HANDLER._reservation_management_service.list_for_waiter_table = MagicMock(
            return_value=WaiterReservationListResponse(reservations=[_view()])
        )

    def test_success_returns_200_with_reservations(self) -> None:
        """A waiter with valid params receives the filtered reservation list."""
        result = self.HANDLER.lambda_handler(_event(_VALID_PARAMS), {})

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(len(payload["reservations"]), 1)
        item = payload["reservations"][0]
        self.assertEqual(item["reservationId"], _RESERVATION_ID)
        self.assertEqual(item["location_address"], "1 Freedom Square, Tbilisi")
        self.assertEqual(item["tableNumber"], 5)
        self.assertEqual(item["date"], "2026-05-16")
        self.assertEqual(item["timeFrom"], "12:00")
        self.assertEqual(item["timeTo"], "13:30")
        self.assertEqual(item["guestsNumber"], 4)
        # Action flags were intentionally removed from this endpoint.
        self.assertNotIn("allowedActions", item)
        self.assertNotIn("cutoffReason", item)

    def test_forwards_validated_params_to_service(self) -> None:
        """The waiter id and query params must be forwarded verbatim to the service."""
        self.HANDLER.lambda_handler(_event(_VALID_PARAMS), {})

        self.HANDLER._reservation_management_service.list_for_waiter_table.assert_called_once_with(
            waiter_id=self.waiter_id,
            date="2026-05-16",
            time_from="12:00",
            table_name="5",
        )

    def test_non_waiter_returns_403(self) -> None:
        """A non-waiter caller is rejected before the service is invoked."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.CUSTOMER)
        )

        result = self.HANDLER.lambda_handler(_event(_VALID_PARAMS), {})

        self.assertEqual(status(result), 403)
        self.HANDLER._reservation_management_service.list_for_waiter_table.assert_not_called()

    def test_missing_authorization_returns_401(self) -> None:
        """A request without an Authorization header is unauthorized."""
        result = self.HANDLER.lambda_handler(_event(_VALID_PARAMS, headers=None), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._reservation_management_service.list_for_waiter_table.assert_not_called()

    def test_missing_required_param_returns_422(self) -> None:
        """Omitting a required query parameter fails validation with 422."""
        result = self.HANDLER.lambda_handler(
            _event({"date": "2026-05-16", "time_from": "12:00"}), {}
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._reservation_management_service.list_for_waiter_table.assert_not_called()

    def test_no_params_returns_422(self) -> None:
        """A request with no query parameters at all fails validation with 422."""
        result = self.HANDLER.lambda_handler(_event(None), {})

        self.assertEqual(status(result), 422)

    def test_malformed_time_returns_422(self) -> None:
        """A malformed time_from value fails the format validator with 422."""
        params = {"date": "2026-05-16", "time_from": "12", "table_name": "5"}
        result = self.HANDLER.lambda_handler(_event(params), {})

        self.assertEqual(status(result), 422)
        self.HANDLER._reservation_management_service.list_for_waiter_table.assert_not_called()

    def test_service_forbidden_error_surfaces_as_403(self) -> None:
        """A service-level 403 (e.g. missing waiter profile) propagates."""
        self.HANDLER._reservation_management_service.list_for_waiter_table = MagicMock(
            side_effect=ApplicationException(
                code=403, content="Waiter profile not found"
            )
        )

        result = self.HANDLER.lambda_handler(_event(_VALID_PARAMS), {})

        self.assertEqual(status(result), 403)
        self.assertEqual(body(result)["message"], "Waiter profile not found")

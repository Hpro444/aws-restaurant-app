"""Tests for reservation dashboard/detail/update/cancel endpoints."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.reservation_management import (
    AllowedActions,
    ReservationListResponse,
    ReservationView,
)
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_LIST_PATH = "/bookings/client"
_RESERVATION_ID = str(uuid4())
_DETAIL_PATH = f"/bookings/client/{_RESERVATION_ID}"
_CANCEL_PATH = f"/bookings/client/{_RESERVATION_ID}/cancel"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


def _reservation_view() -> ReservationView:
    """Build a representative reservation payload for service mocks."""
    return ReservationView(
        reservation_id=_RESERVATION_ID,
        status="RESERVED",
        customer_id=str(uuid4()),
        waiter_id=str(uuid4()),
        location_id=str(uuid4()),
        location_name="1 Freedom Square, Tbilisi",
        table_number=5,
        date="2030-01-01",
        time_from="12:00",
        time_to="13:30",
        guests_number=4,
        allowed_actions=AllowedActions(can_edit=True, can_cancel=True),
        cutoff_reason=None,
    )


class TestReservationManagement(ApiHandlerLambdaTestCase):
    """Covers dashboard and reservation action routes."""

    def setUp(self) -> None:
        """Set default identity and reservation management mocks."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER.value)
        )
        self.HANDLER._reservation_management_service.list_for_dashboard = MagicMock(
            return_value=ReservationListResponse(reservations=[_reservation_view()])
        )
        self.HANDLER._reservation_management_service.get_reservation = MagicMock(
            return_value=_reservation_view()
        )
        self.HANDLER._reservation_management_service.update_reservation = MagicMock(
            return_value=_reservation_view()
        )
        self.HANDLER._reservation_management_service.cancel_reservation = MagicMock(
            return_value=_reservation_view()
        )

    def test_list_dashboard_reservations_returns_200(self) -> None:
        """GET /bookings/client returns reservations for dashboard."""
        result = self.HANDLER.lambda_handler(
            make_event(_LIST_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertIn("reservations", payload)
        self.assertEqual(len(payload["reservations"]), 1)
        item = payload["reservations"][0]
        self.assertEqual(item["status"], "RESERVED")
        self.assertEqual(item["location_name"], "1 Freedom Square, Tbilisi")
        self.assertEqual(item["date"], "2030-01-01")
        self.assertEqual(item["timeFrom"], "12:00")
        self.assertEqual(item["timeTo"], "13:30")
        self.assertEqual(item["guestsNumber"], 4)

    def test_get_reservation_returns_200(self) -> None:
        """GET /bookings/client/{id} returns one reservation payload."""
        result = self.HANDLER.lambda_handler(
            make_event(_DETAIL_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["reservationId"], _RESERVATION_ID)

    def test_update_reservation_returns_200(self) -> None:
        """PUT /bookings/client/{id} edits reservation fields."""
        result = self.HANDLER.lambda_handler(
            make_event(
                _DETAIL_PATH,
                "PUT",
                body={"guestsNumber": 6},
                headers=_VALID_HEADERS,
            ),
            {},
        )

        self.assertEqual(status(result), 200)
        self.HANDLER._reservation_management_service.update_reservation.assert_called_once()

    def test_cancel_reservation_returns_200(self) -> None:
        """DELETE /bookings/client/{id}/cancel performs reservation cancellation."""
        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.HANDLER._reservation_management_service.cancel_reservation.assert_called_once()

    def test_cancel_reservation_passes_correct_ids_to_service(self) -> None:
        """Handler forwards extracted reservation_id and actor_id to the service."""
        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        self.HANDLER._reservation_management_service.cancel_reservation.assert_called_once_with(
            reservation_id=_RESERVATION_ID,
            actor_id=self.customer_id,
            role=UserRole.CUSTOMER.value,
        )

    def test_cancel_reservation_missing_auth_returns_401(self) -> None:
        """DELETE /bookings/client/{id}/cancel without Authorization header returns 401."""
        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE"),
            {},
        )

        self.assertEqual(status(result), 401)

    def test_cancel_reservation_invalid_id_returns_422(self) -> None:
        """Non-UUID segment in cancel path fails request validation with 422."""
        bad_path = "/bookings/client/not-a-uuid/cancel"
        result = self.HANDLER.lambda_handler(
            make_event(bad_path, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)

    def test_cancel_reservation_service_raises_403(self) -> None:
        """Service-level 403 propagates when caller does not own the reservation."""
        self.HANDLER._reservation_management_service.cancel_reservation = MagicMock(
            side_effect=ApplicationException(code=403, content="Forbidden")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)

    def test_cancel_reservation_service_raises_404(self) -> None:
        """Service-level 404 propagates when reservation does not exist."""
        self.HANDLER._reservation_management_service.cancel_reservation = MagicMock(
            side_effect=ApplicationException(code=404, content="Not found")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 404)

    def test_cancel_reservation_within_cutoff_returns_422(self) -> None:
        """Service-level 422 propagates when cancel is attempted within cutoff window."""
        self.HANDLER._reservation_management_service.cancel_reservation = MagicMock(
            side_effect=ApplicationException(code=422, content="Within cutoff window")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_CANCEL_PATH, "DELETE", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)

    def test_invalid_reservation_id_returns_422(self) -> None:
        """Malformed reservationId in path fails request validation."""
        bad_path = "/bookings/client/not-a-uuid"
        result = self.HANDLER.lambda_handler(
            make_event(bad_path, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)

    def test_missing_authorization_returns_401(self) -> None:
        """Missing auth header should short-circuit before service invocation."""
        result = self.HANDLER.lambda_handler(make_event(_LIST_PATH, "GET"), {})
        self.assertEqual(status(result), 401)

    def test_service_forbidden_error_surfaces_as_403(self) -> None:
        """Service-level authorization error propagates with HTTP 403."""
        self.HANDLER._reservation_management_service.get_reservation = MagicMock(
            side_effect=ApplicationException(
                code=403,
                content="You are not allowed to access this reservation",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_DETAIL_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)

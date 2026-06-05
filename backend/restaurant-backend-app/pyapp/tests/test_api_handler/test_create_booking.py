"""Tests for the POST /bookings/client endpoint."""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.create_booking import CreateBookingResponse
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/bookings/client"
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}
_VALID_BODY = {
    "locationId": "672846d5-c951-184d-705b-65d7c951184d",
    "tableNumber": "1",
    "date": _TOMORROW,
    "guestsNumber": "4",
    "timeFrom": f"{_TOMORROW}T12:15:00Z",
    "timeTo": f"{_TOMORROW}T14:00:00Z",
}


def _success_response() -> CreateBookingResponse:
    """Build a representative successful booking response for service mocks."""
    return CreateBookingResponse(
        reservation_id=str(uuid4()),
        status="RESERVED",
        location_id=_VALID_BODY["locationId"],
        location_address="4 Chavchavadze Avenue, Tbilisi",
        table_number=1,
        date=_TOMORROW,
        time_from=f"{_TOMORROW}T12:15:00Z",
        time_to=f"{_TOMORROW}T14:00:00Z",
        guests_number=4,
        client_name=None,
    )


class TestCreateBooking(ApiHandlerLambdaTestCase):
    """Tests for POST /bookings/client."""

    def setUp(self) -> None:
        """Wire a customer identity and a service mock for each test."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER)
        )
        self.HANDLER._booking_service.create_booking = MagicMock(
            return_value=_success_response()
        )
        self.HANDLER._customer_repository.get = MagicMock(return_value=object())

    # ── Success cases ────────────────────────────────────────────────

    def test_single_slot_booking_returns_200_with_reservation_details(self) -> None:
        """A valid request for a single slot returns the reservation payload."""
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(payload["status"], "RESERVED")
        self.assertEqual(payload["tableNumber"], 1)
        self.assertEqual(
            payload["location_address"],
            "4 Chavchavadze Avenue, Tbilisi",
        )
        self.assertEqual(payload["timeFrom"], f"{_TOMORROW}T12:15:00Z")
        self.assertEqual(payload["timeTo"], f"{_TOMORROW}T14:00:00Z")
        self.HANDLER._booking_service.create_booking.assert_called_once()
        kwargs = self.HANDLER._booking_service.create_booking.call_args.kwargs
        self.assertEqual(kwargs["customer_id"], self.customer_id)
        self.assertEqual(kwargs["request"].table_number, 1)
        self.assertEqual(kwargs["request"].guests_number, 4)

    def test_multi_slot_booking_returns_200(self) -> None:
        """A chain spanning two slots also surfaces a single reservation row."""
        multi = CreateBookingResponse(
            reservation_id=str(uuid4()),
            status="RESERVED",
            location_id=_VALID_BODY["locationId"],
            location_address="4 Chavchavadze Avenue, Tbilisi",
            table_number=1,
            date=_TOMORROW,
            time_from=f"{_TOMORROW}T12:15:00Z",
            time_to=f"{_TOMORROW}T15:30:00Z",
            guests_number=4,
        )
        self.HANDLER._booking_service.create_booking = MagicMock(return_value=multi)
        body_ = {**_VALID_BODY, "timeTo": f"{_TOMORROW}T15:30:00Z"}

        event = make_event(_PATH, "POST", body=body_, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["timeTo"], f"{_TOMORROW}T15:30:00Z")

    # ── Authentication / authorisation ──────────────────────────────

    def test_missing_authorization_header_returns_401(self) -> None:
        """No Authorization header yields 401 before the service is touched."""
        event = make_event(_PATH, "POST", body=_VALID_BODY)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 401)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_invalid_token_returns_401(self) -> None:
        """A token rejected by Cognito yields 401."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401, content="Invalid or expired access token"
            )
        )

        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["message"], "Invalid or expired access token")
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_waiter_can_create_visitor_booking(self) -> None:
        """Waiter can create a booking for clientName without customerId."""
        waiter_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(waiter_id, UserRole.WAITER)
        )
        waiter_body = {
            **_VALID_BODY,
            "existingCustomer": False,
            "clientName": "Petar Petrovic",
        }

        event = make_event(_PATH, "POST", body=waiter_body, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 200)
        kwargs = self.HANDLER._booking_service.create_booking.call_args.kwargs
        self.assertIsNone(kwargs["customer_id"])
        self.assertEqual(kwargs["client_name"], "Petar Petrovic")
        self.assertEqual(kwargs["waiter_id"], waiter_id)

    def test_waiter_can_create_existing_customer_booking(self) -> None:
        """Waiter can create a booking for an existing customer via customerId."""
        waiter_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(waiter_id, UserRole.WAITER)
        )
        customer_id = str(uuid4())
        waiter_body = {
            **_VALID_BODY,
            "existingCustomer": True,
            "customerId": customer_id,
        }

        event = make_event(_PATH, "POST", body=waiter_body, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 200)
        kwargs = self.HANDLER._booking_service.create_booking.call_args.kwargs
        self.assertEqual(str(kwargs["customer_id"]), customer_id)
        self.assertIsNone(kwargs["client_name"])
        self.assertEqual(kwargs["waiter_id"], waiter_id)

    def test_waiter_requires_existing_customer_flag(self) -> None:
        """Waiter request without existingCustomer returns 422."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )

        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_waiter_existing_customer_requires_customer_id(self) -> None:
        """Waiter request with existingCustomer=true and no customerId returns 422."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )
        bad = {**_VALID_BODY, "existingCustomer": True}

        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_waiter_non_existing_customer_must_not_send_customer_id(self) -> None:
        """Waiter request with existingCustomer=false and customerId returns 422."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )
        bad = {
            **_VALID_BODY,
            "existingCustomer": False,
            "customerId": str(uuid4()),
            "clientName": "Petar Petrovic",
        }

        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_waiter_non_existing_customer_requires_client_name(self) -> None:
        """Waiter request with existingCustomer=false and no clientName returns 422."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )
        bad = {**_VALID_BODY, "existingCustomer": False}

        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_waiter_existing_customer_not_found_returns_404(self) -> None:
        """Waiter customerId that does not exist is rejected with 404."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )
        self.HANDLER._customer_repository.get = MagicMock(return_value=None)
        bad = {
            **_VALID_BODY,
            "existingCustomer": True,
            "customerId": str(uuid4()),
        }

        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 404)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_customer_cannot_send_existing_customer_or_customer_id(self) -> None:
        """Customer self-booking rejects waiter-specific ownership fields."""
        bad = {
            **_VALID_BODY,
            "existingCustomer": True,
            "customerId": str(uuid4()),
        }

        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_unsupported_role_returns_403(self) -> None:
        """Only customer and waiter roles can create a reservation."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.ADMIN)
        )

        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 403)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    # ── Body validation (422) ───────────────────────────────────────

    def test_missing_required_field_returns_422(self) -> None:
        """Omitting a required field is a 422 with field-level errors."""
        bad = {k: v for k, v in _VALID_BODY.items() if k != "timeFrom"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_invalid_location_uuid_returns_422(self) -> None:
        """A malformed locationId fails Pydantic UUID validation."""
        bad = {**_VALID_BODY, "locationId": "not-a-uuid"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_invalid_time_format_returns_422(self) -> None:
        """TimeFrom outside UTC ISO datetime format is a 422."""
        bad = {**_VALID_BODY, "timeFrom": "12pm"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_inverted_time_window_returns_422(self) -> None:
        """TimeTo not strictly greater than timeFrom is rejected upfront."""
        bad = {
            **_VALID_BODY,
            "timeFrom": f"{_TOMORROW}T14:00:00Z",
            "timeTo": f"{_TOMORROW}T12:15:00Z",
        }
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_time_from_date_must_match_date_returns_422(self) -> None:
        """UTC date portion in timeFrom must equal the date field."""
        other_day = (date.today() + timedelta(days=2)).isoformat()
        bad = {**_VALID_BODY, "timeFrom": f"{other_day}T12:15:00Z"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_past_date_returns_422(self) -> None:
        """A date in the past fails the bookability window check."""
        bad = {**_VALID_BODY, "date": "2020-01-01"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    def test_guests_number_above_max_returns_422(self) -> None:
        """GuestsNumber above the upper bound fails validation."""
        bad = {**_VALID_BODY, "guestsNumber": "11"}
        event = make_event(_PATH, "POST", body=bad, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._booking_service.create_booking.assert_not_called()

    # ── Service-layer errors propagate ──────────────────────────────

    def test_table_not_found_returns_404(self) -> None:
        """ApplicationException(404) from the service surfaces as a 404 response."""
        self.HANDLER._booking_service.create_booking = MagicMock(
            side_effect=ApplicationException(
                code=404, content="Table not found for the specified location"
            )
        )
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 404)
        self.assertEqual(
            body(result)["message"], "Table not found for the specified location"
        )

    def test_capacity_exceeded_returns_422(self) -> None:
        """Guests exceeding capacity is a service-level 422."""
        self.HANDLER._booking_service.create_booking = MagicMock(
            side_effect=ApplicationException(
                code=422,
                content=[
                    {
                        "field": "guestsNumber",
                        "message": "Guests number exceeds table capacity (2)",
                    }
                ],
            )
        )
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)

    def test_time_mismatch_returns_422(self) -> None:
        """A timeFrom that does not match any slot start surfaces as 422."""
        self.HANDLER._booking_service.create_booking = MagicMock(
            side_effect=ApplicationException(
                code=422,
                content=[
                    {
                        "field": "timeFrom",
                        "message": "timeFrom must match the start of an existing slot",
                    }
                ],
            )
        )
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)

    def test_slot_already_reserved_returns_409(self) -> None:
        """A 409 from the service propagates to the response unchanged."""
        self.HANDLER._booking_service.create_booking = MagicMock(
            side_effect=ApplicationException(
                code=409,
                content="One or more selected slots are already reserved",
            )
        )
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)
        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 409)
        self.assertEqual(
            body(result)["message"], "One or more selected slots are already reserved"
        )

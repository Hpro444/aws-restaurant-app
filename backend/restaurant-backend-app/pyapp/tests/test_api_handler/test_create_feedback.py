"""Tests for the POST /feedbacks/ endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from enums import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_PATH = "/feedbacks/"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}
_VALID_BODY = {
    "reservation_id": "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3",
    "type": "service",
    "rating": 5,
    "comment": "Great waiter service.",
}


class TestCreateFeedback(ApiHandlerLambdaTestCase):
    """Tests for customer feedback creation endpoint."""

    def setUp(self) -> None:
        """Set authenticated customer context and feedback service mock."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER)
        )
        self.HANDLER._feedback_service.leave_feedback = MagicMock()

    def test_success_returns_201_with_message(self) -> None:
        """A valid customer request returns created status with success message."""
        event = make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS)

        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 201)
        self.assertEqual(body(result)["message"], "Feedback has been created.")
        self.HANDLER._feedback_service.leave_feedback.assert_called_once()
        kwargs = self.HANDLER._feedback_service.leave_feedback.call_args.kwargs
        self.assertEqual(kwargs["customer_id"], self.customer_id)
        self.assertEqual(
            str(kwargs["request"].reservation_id), _VALID_BODY["reservation_id"]
        )
        self.assertEqual(kwargs["request"].type.value, "service")
        self.assertEqual(kwargs["request"].rating, 5)

    def test_missing_authorization_header_returns_401(self) -> None:
        """Authorization header is required for this route."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=_VALID_BODY), {}
        )

        self.assertEqual(status(result), 401)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_non_customer_role_returns_403(self) -> None:
        """Only customers are allowed to create feedback."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_missing_reservation_id_returns_422(self) -> None:
        """Missing required fields should fail request validation."""
        bad_body = {k: v for k, v in _VALID_BODY.items() if k != "reservation_id"}

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=bad_body, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_legacy_reservation_id_alias_returns_422(self) -> None:
        """CamelCase reservationId is no longer accepted; only reservation_id is valid."""
        bad_body = {
            "reservationId": _VALID_BODY["reservation_id"],
            "type": _VALID_BODY["type"],
            "rating": _VALID_BODY["rating"],
            "comment": _VALID_BODY["comment"],
        }

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=bad_body, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_invalid_type_returns_422(self) -> None:
        """Feedback type must be one of allowed enum values."""
        bad_body = {**_VALID_BODY, "type": "bad-type"}

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=bad_body, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_rating_out_of_range_returns_422(self) -> None:
        """Rating must be in range 1-5."""
        bad_body = {**_VALID_BODY, "rating": 6}

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=bad_body, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.leave_feedback.assert_not_called()

    def test_service_not_found_error_returns_404(self) -> None:
        """Service-layer not-found errors should be propagated."""
        self.HANDLER._feedback_service.leave_feedback = MagicMock(
            side_effect=ApplicationException(404, "Reservation not found")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "POST", body=_VALID_BODY, headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Reservation not found")

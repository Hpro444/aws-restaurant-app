"""Tests for the GET /feedbacks/context/{reservation_id} endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.feedbacks import FeedbackContextResponse
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_RESERVATION_ID = "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3"
_PATH = f"/feedbacks/context/{_RESERVATION_ID}"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


class TestFeedbackContext(ApiHandlerLambdaTestCase):
    """Tests for feedback modal context endpoint."""

    def setUp(self) -> None:
        """Set authenticated customer context and feedback service mock."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER)
        )
        self.HANDLER._feedback_service.get_feedback_context = MagicMock(
            return_value=FeedbackContextResponse(
                reservation_id=_RESERVATION_ID,
                waiter_id=str(uuid4()),
                waiter_name="Mario Jast",
                waiter_image_url="https://example.com/waiter.png",
            )
        )

    def test_success_returns_200_with_waiter_context(self) -> None:
        """Customer should get modal context for their reservation."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(payload["reservation_id"], _RESERVATION_ID)
        self.assertEqual(payload["waiter_name"], "Mario Jast")
        self.HANDLER._feedback_service.get_feedback_context.assert_called_once_with(
            reservation_id=_RESERVATION_ID,
            customer_id=self.customer_id,
        )

    def test_missing_authorization_header_returns_401(self) -> None:
        """Authorization header is required for this route."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._feedback_service.get_feedback_context.assert_not_called()

    def test_non_customer_role_returns_403(self) -> None:
        """Only customers are allowed to fetch feedback context."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.HANDLER._feedback_service.get_feedback_context.assert_not_called()

    def test_invalid_reservation_id_returns_422(self) -> None:
        """Malformed reservation_id in path should fail request validation."""
        result = self.HANDLER.lambda_handler(
            make_event("/feedbacks/context/not-a-uuid", "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedback_context.assert_not_called()

    def test_service_not_found_error_returns_404(self) -> None:
        """Service-layer not-found errors should be propagated."""
        self.HANDLER._feedback_service.get_feedback_context = MagicMock(
            side_effect=ApplicationException(404, "Reservation not found")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Reservation not found")

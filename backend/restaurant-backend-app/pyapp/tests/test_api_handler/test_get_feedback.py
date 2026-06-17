"""Tests for the GET /feedback/{reservation_id} endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_RESERVATION_ID = "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3"
_PATH = f"/feedback/{_RESERVATION_ID}"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


class TestGetFeedbackByReservation(ApiHandlerLambdaTestCase):
    """Tests for feedback by reservation endpoint."""

    def setUp(self) -> None:
        """Set authenticated customer context and feedback service mock."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.feedback_id_1 = str(uuid4())
        self.feedback_id_2 = str(uuid4())
        self.location_id = str(uuid4())
        self.waiter_id = str(uuid4())

        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER)
        )
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id = MagicMock(
            return_value={
                "CuisineFeedback": {
                    "id": self.feedback_id_1,
                    "customer_id": self.customer_id,
                    "feedback": "Excellent food",
                    "rate": 5,
                    "date": datetime.now(UTC).isoformat(),
                    "user_name": "Alice Johnson",
                    "user_image_url": "https://images.example.com/users/alice.png",
                    "location_id": self.location_id,
                    "waiter_id": None,
                },
                "ServiceFeedback": {
                    "id": self.feedback_id_2,
                    "customer_id": self.customer_id,
                    "feedback": "Great service",
                    "rate": 5,
                    "date": datetime.now(UTC).isoformat(),
                    "user_name": "Alice Johnson",
                    "user_image_url": "https://images.example.com/users/alice.png",
                    "location_id": None,
                    "waiter_id": self.waiter_id,
                },
            }
        )

    def test_success_returns_200_with_both_feedbacks(self) -> None:
        """Customer should get both feedbacks when both exist for reservation."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertIsInstance(payload, dict)
        self.assertIn("CuisineFeedback", payload)
        self.assertIn("ServiceFeedback", payload)
        self.assertEqual(payload["CuisineFeedback"]["id"], self.feedback_id_1)
        self.assertEqual(payload["ServiceFeedback"]["id"], self.feedback_id_2)
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id.assert_called_once_with(
            reservation_id=_RESERVATION_ID,
            customer_id=self.customer_id,
        )

    def test_returns_200_with_only_cuisine_feedback(self) -> None:
        """Customer should get cuisine feedback when service feedback is None."""
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id = MagicMock(
            return_value={
                "CuisineFeedback": {
                    "id": self.feedback_id_1,
                    "customer_id": self.customer_id,
                    "feedback": "Excellent food",
                    "rate": 5,
                    "date": datetime.now(UTC).isoformat(),
                    "user_name": "Alice Johnson",
                    "user_image_url": "https://images.example.com/users/alice.png",
                    "location_id": self.location_id,
                    "waiter_id": None,
                },
                "ServiceFeedback": None,
            }
        )
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertIsNotNone(payload["CuisineFeedback"])
        self.assertIsNone(payload["ServiceFeedback"])

    def test_returns_200_with_both_none_when_no_feedbacks(self) -> None:
        """Customer should get both as None when no feedbacks exist for reservation."""
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id = MagicMock(
            return_value={
                "CuisineFeedback": None,
                "ServiceFeedback": None,
            }
        )
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertIsNone(payload["CuisineFeedback"])
        self.assertIsNone(payload["ServiceFeedback"])

    def test_missing_authorization_header_returns_401(self) -> None:
        """Authorization header is required for this route."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id.assert_not_called()

    def test_non_customer_role_returns_403(self) -> None:
        """Only customers are allowed to fetch feedback details."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"],
            "Only customers can access feedback details.",
        )
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id.assert_not_called()

    def test_invalid_reservation_id_returns_422(self) -> None:
        """Malformed reservation_id in path should fail request validation."""
        result = self.HANDLER.lambda_handler(
            make_event("/feedback/not-a-uuid", "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id.assert_not_called()

    def test_service_not_found_error_returns_404(self) -> None:
        """Service-layer not-found errors should be propagated."""
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id = MagicMock(
            side_effect=ApplicationException(404, "Reservation not found")
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Reservation not found")

    def test_service_forbidden_error_returns_403(self) -> None:
        """Service-layer ownership violations should be propagated as forbidden."""
        self.HANDLER._feedback_service.get_feedbacks_by_reservation_id = MagicMock(
            side_effect=ApplicationException(
                403,
                "Not authorized to access feedbacks for this reservation.",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"],
            "Not authorized to access feedbacks for this reservation.",
        )

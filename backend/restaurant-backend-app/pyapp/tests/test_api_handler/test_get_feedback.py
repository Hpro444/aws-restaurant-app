"""Tests for the GET /feedback/{feedback_id} endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.feedbacks import FeedbackResponse
from enums.user_role import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_FEEDBACK_ID = "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3"
_PATH = f"/feedback/{_FEEDBACK_ID}"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}
_VALID_QUERY = {"type": "service"}


class TestGetFeedback(ApiHandlerLambdaTestCase):
    """Tests for single feedback details endpoint."""

    def setUp(self) -> None:
        """Set authenticated customer context and feedback service mock."""
        super().setUp()
        self.customer_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.customer_id, UserRole.CUSTOMER)
        )
        self.HANDLER._feedback_service.get_feedback = MagicMock(
            return_value=FeedbackResponse(
                id=_FEEDBACK_ID,
                customer_id=self.customer_id,
                feedback="Great service",
                rate=5,
                date=datetime.now(UTC),
                user_name="Alice Johnson",
                user_image_url="https://images.example.com/users/alice.png",
                waiter_id=str(uuid4()),
            )
        )

    def test_success_returns_200_with_feedback_payload(self) -> None:
        """Customer should get full feedback details for owned feedback id."""
        event = make_event(_PATH, "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = _VALID_QUERY
        result = self.HANDLER.lambda_handler(
            event,
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(payload["id"], _FEEDBACK_ID)
        self.assertEqual(payload["customer_id"], self.customer_id)
        self.assertEqual(payload["feedback"], "Great service")
        self.assertEqual(payload["rate"], 5)
        self.HANDLER._feedback_service.get_feedback.assert_called_once_with(
            feedback_id=_FEEDBACK_ID,
            customer_id=self.customer_id,
            type="service",
        )

    def test_missing_authorization_header_returns_401(self) -> None:
        """Authorization header is required for this route."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._feedback_service.get_feedback.assert_not_called()

    def test_non_customer_role_returns_403(self) -> None:
        """Only customers are allowed to fetch feedback details."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )
        event = make_event(_PATH, "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = _VALID_QUERY

        result = self.HANDLER.lambda_handler(
            event,
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"],
            "Only customers can access feedback details.",
        )
        self.HANDLER._feedback_service.get_feedback.assert_not_called()

    def test_invalid_feedback_id_returns_422(self) -> None:
        """Malformed feedback_id in path should fail request validation."""
        event = make_event("/feedback/not-a-uuid", "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = _VALID_QUERY
        result = self.HANDLER.lambda_handler(
            event,
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedback.assert_not_called()

    def test_missing_type_query_param_returns_422(self) -> None:
        """Feedback type is required."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedback.assert_not_called()

    def test_invalid_type_query_param_returns_422(self) -> None:
        """Feedback type must be cuisine or service."""
        event = make_event(_PATH, "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = {"type": "invalid"}

        result = self.HANDLER.lambda_handler(event, {})

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedback.assert_not_called()

    def test_not_found_returns_200_with_empty_list(self) -> None:
        """Valid UUID with no feedback should return empty list."""
        self.HANDLER._feedback_service.get_feedback = MagicMock(return_value=[])
        event = make_event(_PATH, "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = _VALID_QUERY

        result = self.HANDLER.lambda_handler(
            event,
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])

    def test_service_forbidden_error_returns_403(self) -> None:
        """Service-layer ownership violations should be propagated as forbidden."""
        self.HANDLER._feedback_service.get_feedback = MagicMock(
            side_effect=ApplicationException(
                403,
                "Not authorized to access this feedback.",
            )
        )
        event = make_event(_PATH, "GET", headers=_VALID_HEADERS)
        event["queryStringParameters"] = _VALID_QUERY

        result = self.HANDLER.lambda_handler(
            event,
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"],
            "Not authorized to access this feedback.",
        )

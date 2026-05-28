"""Tests for the GET /locations/{id}/feedbacks endpoint."""

from uuid import UUID

from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase, body, status

_LOCATION_ID = "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3"
_PATH = f"/locations/{_LOCATION_ID}/feedbacks"


class _FeedbackItem:
    """Simple test helper to mimic a Pydantic model with model_dump."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def model_dump(self, mode: str | None = None) -> dict:
        return self._payload


class TestFeedbacks(ApiHandlerLambdaTestCase):
    """Tests for the public feedbacks endpoint by location."""

    def test_success_returns_200_with_paginated_payload(self) -> None:
        """A valid request should return a paginated payload and call service once."""
        self.HANDLER._feedback_service.get_feedbacks.return_value = {
            "totalPages": 1,
            "totalElements": 1,
            "size": 10,
            "content": [
                _FeedbackItem(
                    {
                        "id": "11111111-1111-4111-8111-111111111111",
                        "customer_id": "22222222-2222-4222-8222-222222222222",
                        "feedback": "Great service",
                        "rate": 5,
                        "date": "2026-05-20T10:00:00Z",
                        "user_name": "Alice Johnson",
                        "user_image_url": "https://images.example.com/users/alice.png",
                        "waiter_id": "33333333-3333-4333-8333-333333333333",
                    }
                )
            ],
            "number": 0,
            "sort": ["date,desc"],
            "first": True,
            "last": True,
            "numberOfElements": 1,
            "pageable": {
                "offset": 0,
                "sort": ["date,desc"],
                "paged": True,
                "pageSize": 10,
                "pageNumber": 0,
                "unpaged": False,
            },
            "empty": False,
        }

        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {
                    "type": "service",
                    "sort": "date,desc",
                    "page": "0",
                    "size": "10",
                },
            },
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(payload["totalElements"], 1)
        self.assertEqual(payload["content"][0]["feedback"], "Great service")
        self.assertEqual(payload["content"][0]["rate"], 5)
        self.assertEqual(payload["content"][0]["user_name"], "Alice Johnson")
        self.assertEqual(
            payload["content"][0]["user_image_url"],
            "https://images.example.com/users/alice.png",
        )
        self.HANDLER._feedback_service.get_feedbacks.assert_called_once_with(
            location_id=UUID(_LOCATION_ID),
            type="service",
            sort=["date,desc"],
            page=0,
            size=10,
        )

    def test_missing_type_returns_422(self) -> None:
        """Type is required and should return 422 when missing."""
        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {},
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedbacks.assert_not_called()

    def test_invalid_type_returns_422(self) -> None:
        """Type must be either cuisine or service."""
        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {"type": "invalid"},
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedbacks.assert_not_called()

    def test_invalid_sort_field_returns_422(self) -> None:
        """Sort field must be either date or rate."""
        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {"type": "cuisine", "sort": "id,desc"},
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedbacks.assert_not_called()

    def test_invalid_location_id_returns_422(self) -> None:
        """A malformed location id in the path should return 422."""
        result = self.HANDLER.lambda_handler(
            {
                "path": "/locations/not-a-uuid/feedbacks",
                "httpMethod": "GET",
                "queryStringParameters": {"type": "cuisine"},
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._feedback_service.get_feedbacks.assert_not_called()

    def test_default_pagination_and_sort_are_used(self) -> None:
        """When omitted, sort/page/size should use endpoint defaults."""
        self.HANDLER._feedback_service.get_feedbacks.return_value = {
            "totalPages": 0,
            "totalElements": 0,
            "size": 20,
            "content": [],
            "number": 0,
            "sort": ["date,desc"],
            "first": True,
            "last": True,
            "numberOfElements": 0,
            "pageable": {
                "offset": 0,
                "sort": ["date,desc"],
                "paged": True,
                "pageSize": 20,
                "pageNumber": 0,
                "unpaged": False,
            },
            "empty": True,
        }

        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {"type": "cuisine"},
            },
            {},
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result)["content"], [])
        self.HANDLER._feedback_service.get_feedbacks.assert_called_once_with(
            location_id=UUID(_LOCATION_ID),
            type="cuisine",
            sort=["date,desc"],
            page=0,
            size=20,
        )

    def test_page_out_of_range_returns_422(self) -> None:
        """A requested page greater than last page should return 422 validation error."""
        self.HANDLER._feedback_service.get_feedbacks.return_value = {
            "totalPages": 3,
            "totalElements": 30,
            "size": 10,
            "content": [],
            "number": 20,
            "sort": ["date,desc"],
            "first": False,
            "last": False,
            "numberOfElements": 0,
            "pageable": {
                "offset": 200,
                "sort": ["date,desc"],
                "paged": True,
                "pageSize": 10,
                "pageNumber": 20,
                "unpaged": False,
            },
            "empty": True,
        }

        result = self.HANDLER.lambda_handler(
            {
                "path": _PATH,
                "httpMethod": "GET",
                "queryStringParameters": {
                    "type": "cuisine",
                    "page": "20",
                    "size": "10",
                },
            },
            {},
        )

        self.assertEqual(status(result), 422)
        payload = body(result)
        self.assertEqual(payload["errors"][0]["field"], "page")
        self.assertEqual(payload["errors"][0]["message"], "Must be between 0 and 2")

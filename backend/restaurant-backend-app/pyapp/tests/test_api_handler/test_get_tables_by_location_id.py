"""Tests for the GET /locations/{id}/tables endpoint."""

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

_LOCATION_ID = str(uuid4())
_PATH = f"/locations/{_LOCATION_ID}/tables"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


def _make_table(table_number: int) -> MagicMock:
    """Return a mock Table domain object with the given table_number."""
    t = MagicMock()
    t.table_number = table_number
    return t


class TestGetTablesByLocationId(ApiHandlerLambdaTestCase):
    """Tests for the waiter-only GET /locations/{id}/tables endpoint."""

    def setUp(self) -> None:
        """Set default waiter identity and mock service response."""
        super().setUp()
        self.waiter_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.waiter_id, UserRole.WAITER)
        )
        self.HANDLER._table_availability_service.get_tables_by_location_id = MagicMock(
            return_value=[_make_table(1), _make_table(2), _make_table(3)]
        )

    def test_returns_200_with_table_list(self) -> None:
        """Waiter receives a 200 with the list of table numbers."""
        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS), {}
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(len(payload), 3)
        self.assertEqual([t["table_number"] for t in payload], [1, 2, 3])
        self.HANDLER._table_availability_service.get_tables_by_location_id.assert_called_once()

    def test_returns_200_with_empty_list(self) -> None:
        """Waiter receives an empty list when no tables exist at the location."""
        self.HANDLER._table_availability_service.get_tables_by_location_id = MagicMock(
            return_value=[]
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS), {}
        )

        self.assertEqual(status(result), 200)
        self.assertEqual(body(result), [])

    def test_missing_auth_header_returns_401(self) -> None:
        """Missing Authorization header returns 401."""
        result = self.HANDLER.lambda_handler(make_event(_PATH, "GET"), {})

        self.assertEqual(status(result), 401)
        self.HANDLER._table_availability_service.get_tables_by_location_id.assert_not_called()

    def test_invalid_token_returns_401(self) -> None:
        """Invalid or expired token returns 401."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401,
                content="Invalid or expired access token",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS), {}
        )

        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["message"], "Invalid or expired access token")
        self.HANDLER._table_availability_service.get_tables_by_location_id.assert_not_called()

    def test_non_waiter_role_returns_403(self) -> None:
        """Non-waiter callers receive 403."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.CUSTOMER)
        )

        result = self.HANDLER.lambda_handler(
            make_event(_PATH, "GET", headers=_VALID_HEADERS), {}
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(
            body(result)["message"], "Only waiters can access tables list."
        )
        self.HANDLER._table_availability_service.get_tables_by_location_id.assert_not_called()

    def test_invalid_location_uuid_returns_422(self) -> None:
        """A non-UUID location id returns 422."""
        result = self.HANDLER.lambda_handler(
            make_event("/locations/not-a-uuid/tables", "GET", headers=_VALID_HEADERS),
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_tables_by_location_id.assert_not_called()

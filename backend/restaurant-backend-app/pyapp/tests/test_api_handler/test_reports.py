"""Tests for the GET /reports endpoint."""

from unittest.mock import MagicMock
from uuid import uuid4

from commons.exceptions import ApplicationException
from dto.reports import ReportType
from enums import UserRole
from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_get_event,
    status,
)

_PATH = "/reports"
_VALID_HEADERS = {"Authorization": "Bearer valid-token"}


class TestReports(ApiHandlerLambdaTestCase):
    """Tests for GET /reports admin-protected endpoint."""

    def setUp(self) -> None:
        """Set default admin identity and service return value."""
        super().setUp()
        self.admin_id = str(uuid4())
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(self.admin_id, UserRole.ADMIN)
        )
        self.HANDLER._reports_service.get_reports = MagicMock(
            return_value=MagicMock(
                model_dump=MagicMock(
                    return_value={
                        "reportType": "staff_performance",
                        "periodStart": "2026-06-01",
                        "periodEnd": "2026-06-07",
                        "rows": [
                            {
                                "location": "Location 1",
                                "waiter": "Alex Coper",
                                "waiterOrdersProcessed": 40,
                            }
                        ],
                    }
                )
            )
        )

    def test_get_reports_returns_200_for_admin(self) -> None:
        """Admin should receive report payload with 200."""
        result = self.HANDLER.lambda_handler(
            make_get_event(
                _PATH,
                {
                    "reportType": "staff_performance",
                    "periodStart": "2026-06-04",
                    "periodEnd": "2026-06-10",
                },
            )
            | {"headers": _VALID_HEADERS},
            {},
        )

        self.assertEqual(status(result), 200)
        payload = body(result)
        self.assertEqual(payload["reportType"], "staff_performance")
        self.assertEqual(payload["periodStart"], "2026-06-01")
        self.assertEqual(payload["rows"][0]["waiter"], "Alex Coper")

        call_args = self.HANDLER._reports_service.get_reports.call_args.args[0]
        self.assertEqual(call_args.report_type, ReportType.STAFF_PERFORMANCE)
        self.assertEqual(call_args.period_start, "2026-06-04")
        self.assertEqual(call_args.period_end, "2026-06-10")

    def test_missing_authorization_header_returns_401(self) -> None:
        """Missing Authorization header should return 401."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"periodStart": "2026-06-04"}),
            {},
        )

        self.assertEqual(status(result), 401)
        self.HANDLER._reports_service.get_reports.assert_not_called()

    def test_non_admin_role_returns_403(self) -> None:
        """Only admin role can access GET /reports."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            return_value=(str(uuid4()), UserRole.WAITER)
        )

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"periodStart": "2026-06-04"})
            | {"headers": _VALID_HEADERS},
            {},
        )

        self.assertEqual(status(result), 403)
        self.assertEqual(body(result)["message"], "Only admins can access reports.")
        self.HANDLER._reports_service.get_reports.assert_not_called()

    def test_invalid_period_returns_422(self) -> None:
        """Invalid period input should return 422 from request validation."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"periodStart": "not-a-date"})
            | {"headers": _VALID_HEADERS},
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._reports_service.get_reports.assert_not_called()

    def test_future_period_returns_422(self) -> None:
        """Future period start/end values should be rejected with 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(
                _PATH,
                {
                    "periodStart": "2099-01-01",
                    "periodEnd": "2099-01-07",
                },
            )
            | {"headers": _VALID_HEADERS},
            {},
        )

        self.assertEqual(status(result), 422)
        self.HANDLER._reports_service.get_reports.assert_not_called()

    def test_invalid_token_returns_401(self) -> None:
        """Invalid token should return 401 and not call reports service."""
        self.HANDLER._cognito_service.get_identity_from_access_token = MagicMock(
            side_effect=ApplicationException(
                code=401,
                content="Invalid or expired access token",
            )
        )

        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {"periodStart": "2026-06-04"})
            | {"headers": _VALID_HEADERS},
            {},
        )

        self.assertEqual(status(result), 401)
        self.assertEqual(body(result)["message"], "Invalid or expired access token")
        self.HANDLER._reports_service.get_reports.assert_not_called()

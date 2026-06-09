"""Tests for report sender lambda success path."""

import json
from unittest.mock import patch

from pyapp.tests.test_report_sender_lambda import ReportSenderLambdaTestCase


class TestSuccess(ReportSenderLambdaTestCase):
    """Verify lambda delegates weekly report sending to service layer."""

    @patch("lambdas.report_sender_lambda.handler.ReportSenderService")
    def test_success(self, report_sender_service_cls):
        """Assert handler returns 200 with service summary payload."""
        report_sender_service_cls.return_value.send_weekly_report.return_value = {
            "report_period_start": "2026-06-08",
            "report_period_end": "2026-06-14",
            "waiter_rows": 3,
            "location_rows": 2,
            "recipient": "recipient_test@gmail.com",
        }

        handler = self.HANDLER.__class__()
        result = handler.handle_request({}, {})

        payload = json.loads(result.body)
        self.assertEqual(payload["report_period_start"], "2026-06-08")
        self.assertEqual(payload["waiter_rows"], 3)
        self.assertEqual(payload["location_rows"], 2)

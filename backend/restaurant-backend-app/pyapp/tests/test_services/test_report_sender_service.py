"""Unit tests for ReportSenderService CSV generation and SES delivery."""

from datetime import date
from email import message_from_string
from unittest import TestCase
from unittest.mock import MagicMock
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.app_config import AppConfig
    from domain.location_report import LocationReport
    from domain.waiter_report import WaiterReport
    from services.report_sender_service import ReportSenderService


def _make_waiter_report() -> WaiterReport:
    """Return a minimal WaiterReport row for weekly CSV tests."""
    return WaiterReport(
        id=uuid4(),
        waiter_id=uuid4(),
        location_id=uuid4(),
        location_name="Location 1",
        waiter_first_name="Alex",
        waiter_last_name="Coper",
        waiter_email="alexcop@gmail.com",
        report_period_start="2026-06-08",
        report_period_end="2026-06-14",
        working_hours=30.0,
        orders_processed=40,
        service_feedback_count=3,
        service_feedback_sum=12.6,
        avg_service_feedback=4.2,
        min_service_feedback=3,
        orders_processed_delta_pct=10.0,
        avg_service_feedback_delta_pct=5.0,
    )


def _make_location_report() -> LocationReport:
    """Return a minimal LocationReport row for weekly CSV tests."""
    return LocationReport(
        id=uuid4(),
        location_id=uuid4(),
        location_name="Location 1",
        report_period_start="2026-06-08",
        report_period_end="2026-06-14",
        orders_processed=465,
        orders_processed_delta_pct=3.0,
        cuisine_feedback_count=3,
        cuisine_feedback_sum=13.8,
        avg_cuisine_feedback=4.6,
        min_cuisine_feedback=3,
        avg_cuisine_feedback_delta_pct=-3.0,
        revenue=44175.0,
        revenue_delta_pct=3.0,
    )


class TestReportSenderService(TestCase):
    """Tests for compiling report tables and sending email attachments."""

    def test_sends_current_week_report_with_two_csv_attachments(self):
        """Service reads period rows and sends SES raw email with both CSV files."""
        waiter_report_repo = MagicMock()
        waiter_report_repo.find_by_period_start.return_value = [_make_waiter_report()]

        location_report_repo = MagicMock()
        location_report_repo.find_by_period_start.return_value = [
            _make_location_report()
        ]

        ses_client = MagicMock()
        settings = AppConfig(
            aws_region="eu-west-3",
            report_sender_email="sender_test@gmail.com",
            report_recipient_email="recipient_test@gmail.com",
        )

        service = ReportSenderService(
            settings=settings,
            waiter_report_repo=waiter_report_repo,
            location_report_repo=location_report_repo,
            ses_client=ses_client,
        )

        summary = service.send_weekly_report(target_date=date(2026, 6, 9))

        waiter_report_repo.find_by_period_start.assert_called_once_with("2026-06-08")
        location_report_repo.find_by_period_start.assert_called_once_with("2026-06-08")
        ses_client.send_raw_email.assert_called_once()

        call_kwargs = ses_client.send_raw_email.call_args.kwargs
        self.assertEqual(call_kwargs["Source"], "sender_test@gmail.com")
        self.assertEqual(call_kwargs["Destinations"], ["recipient_test@gmail.com"])

        raw_data = call_kwargs["RawMessage"]["Data"]
        self.assertIn("waiter_report.csv", raw_data)
        self.assertIn("location_report.csv", raw_data)

        mime = message_from_string(raw_data)
        attachments = {
            part.get_filename(): part.get_payload(decode=True).decode("utf-8")
            for part in mime.walk()
            if part.get_filename()
        }
        self.assertIn(
            "Location,Waiter,Waiter's e-mail", attachments["waiter_report.csv"]
        )
        self.assertIn(
            "Location,Report period start,Report period end",
            attachments["location_report.csv"],
        )

        self.assertEqual(summary["report_period_start"], "2026-06-08")
        self.assertEqual(summary["report_period_end"], "2026-06-14")
        self.assertEqual(summary["waiter_rows"], 1)
        self.assertEqual(summary["location_rows"], 1)

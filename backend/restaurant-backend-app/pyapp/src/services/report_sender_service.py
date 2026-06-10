"""Service for compiling weekly reports and emailing CSV attachments via SES."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage
from io import StringIO
from typing import Any

import boto3
from commons.app_config import AppConfig
from commons.report_utils import period_end_for, period_start_for
from repositories.location_report_repository import LocationReportRepository
from repositories.waiter_report_repository import WaiterReportRepository


class ReportSenderService:
    """Builds weekly report CSV files and delivers them by email."""

    def __init__(
        self,
        settings: AppConfig | None = None,
        waiter_report_repo: WaiterReportRepository | None = None,
        location_report_repo: LocationReportRepository | None = None,
        ses_client: Any | None = None,
    ) -> None:
        """Initialise repositories and SES client."""
        cfg = settings or AppConfig()
        self._settings = cfg
        self._waiter_report_repo = waiter_report_repo or WaiterReportRepository(cfg)
        self._location_report_repo = location_report_repo or LocationReportRepository(
            cfg
        )
        self._ses = ses_client or boto3.client("ses", region_name=cfg.aws_region)

    def send_weekly_report(self, target_date: date | None = None) -> dict[str, Any]:
        """Compile previous-week reports and send them as CSV attachments."""
        report_date = target_date or datetime.now(UTC).date()
        previous_week_date = report_date - timedelta(days=7)
        period_start = period_start_for(previous_week_date)
        period_end = period_end_for(period_start)
        period_start_iso = period_start.isoformat()

        waiter_reports = self._waiter_report_repo.find_by_period_start(period_start_iso)
        location_reports = self._location_report_repo.find_by_period_start(
            period_start_iso
        )

        waiter_csv = self._build_waiter_csv(waiter_reports)
        location_csv = self._build_location_csv(location_reports)

        self._send_email_with_attachments(
            waiter_csv=waiter_csv,
            location_csv=location_csv,
            period_start=period_start,
            period_end=period_end,
        )

        return {
            "report_period_start": period_start_iso,
            "report_period_end": period_end.isoformat(),
            "waiter_rows": len(waiter_reports),
            "location_rows": len(location_reports),
            "recipient": self._settings.report_recipient_email,
        }

    def _build_waiter_csv(self, reports: list[Any]) -> str:
        """Create the staff performance CSV."""
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "Location",
                "Waiter",
                "Waiter's e-mail",
                "Report period start",
                "Report period end",
                "Waiter working hours",
                "Waiter Orders processed",
                "Delta of Waiter Orders processed to previous period in %",
                "Average Service Feedback Waiter (1 to 5)",
                "Minimum Service Feedback Waiter (1 to 5)",
                "Delta of Average Service Feedback Waiter to previous period in %",
            ]
        )

        sorted_reports = sorted(
            reports,
            key=lambda r: (
                (r.location_name or "").lower(),
                (r.waiter_last_name or "").lower(),
                (r.waiter_first_name or "").lower(),
            ),
        )
        for report in sorted_reports:
            writer.writerow(
                [
                    report.location_name,
                    f"{report.waiter_first_name} {report.waiter_last_name}",
                    report.waiter_email,
                    report.report_period_start,
                    report.report_period_end,
                    self._format_number(report.working_hours),
                    report.orders_processed,
                    self._format_pct(report.orders_processed_delta_pct),
                    self._format_number(report.avg_service_feedback),
                    self._format_number(report.min_service_feedback),
                    self._format_pct(report.avg_service_feedback_delta_pct),
                ]
            )
        return output.getvalue()

    def _build_location_csv(self, reports: list[Any]) -> str:
        """Create the location comparison CSV."""
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "Location",
                "Report period start",
                "Report period end",
                "Orders processed within location",
                "Delta of orders processed within location to previous period (in %)",
                "Average cuisine Feedback by Restaurant location (1 to 5)",
                "Minimum cuisine Feedback by Restaurant location (1 to 5)",
                "Delta of average cuisine Feedback by Restaurant location to previous period (in %)",
                "Revenue for orders within reported period (USD)",
                "Delta of revenue for orders to previous period %",
            ]
        )

        sorted_reports = sorted(reports, key=lambda r: (r.location_name or "").lower())
        for report in sorted_reports:
            writer.writerow(
                [
                    report.location_name,
                    report.report_period_start,
                    report.report_period_end,
                    report.orders_processed,
                    self._format_pct(report.orders_processed_delta_pct),
                    self._format_number(report.avg_cuisine_feedback),
                    self._format_number(report.min_cuisine_feedback),
                    self._format_pct(report.avg_cuisine_feedback_delta_pct),
                    self._format_number(report.revenue),
                    self._format_pct(report.revenue_delta_pct),
                ]
            )
        return output.getvalue()

    def _send_email_with_attachments(
        self,
        waiter_csv: str,
        location_csv: str,
        period_start: date,
        period_end: date,
    ) -> None:
        """Send a single email with both report CSV files attached."""
        sender = self._settings.report_sender_email
        recipient = self._settings.report_recipient_email
        if not sender or not recipient:
            raise ValueError("Report sender and recipient emails must be configured")

        msg = EmailMessage()
        msg["Subject"] = (
            "Weekly Restaurant Reports "
            f"({period_start.isoformat()} - {period_end.isoformat()})"
        )
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(
            "Attached are weekly staff performance and location comparison reports."
        )

        msg.add_attachment(
            waiter_csv.encode("utf-8"),
            maintype="text",
            subtype="csv",
            filename="waiter_report.csv",
        )
        msg.add_attachment(
            location_csv.encode("utf-8"),
            maintype="text",
            subtype="csv",
            filename="location_report.csv",
        )

        self._ses.send_raw_email(
            Source=sender,
            Destinations=[recipient],
            RawMessage={"Data": msg.as_string()},
        )

    @staticmethod
    def _format_pct(value: float | None) -> str:
        """Render percentage values with sign and trailing percent symbol."""
        if value is None:
            return ""
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        sign = "+" if value > 0 else ""
        return f"{sign}{formatted}%"

    @staticmethod
    def _format_number(value: float | int | None) -> str | int:
        """Render numeric values compactly while keeping empty values blank."""
        if value is None:
            return ""
        if isinstance(value, int):
            return value
        return f"{value:.2f}".rstrip("0").rstrip(".")

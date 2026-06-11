"""Service for admin reporting dashboard table data."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import boto3
from commons.app_config import AppConfig
from commons.report_utils import parse_date, pct_delta, period_start_for
from dto.reports import (
    CreateReportsDownloadRequest,
    DownloadFormat,
    GetReportsRequest,
    ReportsResponse,
    ReportType,
)
from repositories.location_report_repository import LocationReportRepository
from repositories.waiter_report_repository import WaiterReportRepository

_STAFF_COLUMN_LABELS: dict[str, str] = {
    "location": "Location",
    "waiter": "Waiter",
    "waiterEmail": "Waiter Email",
    "reportPeriodStart": "Period Start",
    "reportPeriodEnd": "Period End",
    "waiterWorkingHours": "Working Hours",
    "waiterOrdersProcessed": "Orders Processed",
    "deltaWaiterOrdersProcessedPct": "Delta Orders %",
    "averageServiceFeedback": "Avg Service Rating",
    "minimumServiceFeedback": "Min Service Rating",
    "deltaAverageServiceFeedbackPct": "Delta Rating %",
}

_SALES_COLUMN_LABELS: dict[str, str] = {
    "location": "Location",
    "reportPeriodStart": "Period Start",
    "reportPeriodEnd": "Period End",
    "ordersProcessed": "Orders Processed",
    "deltaOrdersProcessedPct": "Delta Orders %",
    "averageCuisineFeedback": "Avg Cuisine Rating",
    "minimumCuisineFeedback": "Min Cuisine Rating",
    "deltaAverageCuisineFeedbackPct": "Delta Cuisine Rating %",
    "revenue": "Revenue",
    "deltaRevenuePct": "Delta Revenue %",
}


class ReportsService:
    """Builds filtered report-table rows for the reporting UI."""

    def __init__(
        self,
        settings: AppConfig | None = None,
        waiter_report_repo: WaiterReportRepository | None = None,
        location_report_repo: LocationReportRepository | None = None,
    ) -> None:
        """Initialise repositories, creating defaults when omitted."""
        cfg = settings or AppConfig()
        self._settings = cfg
        self._waiter_report_repo = waiter_report_repo or WaiterReportRepository(cfg)
        self._location_report_repo = location_report_repo or LocationReportRepository(
            cfg
        )
        self._s3 = boto3.client("s3", region_name=cfg.aws_region)

    def get_reports(self, request: GetReportsRequest) -> ReportsResponse:
        """Return report rows for requested type, period range, and optional location."""
        period_start, period_end = request.resolve_period_range()
        duration_days = (period_end - period_start).days
        prev_period_end = period_start - timedelta(days=1)
        prev_period_start = prev_period_end - timedelta(days=duration_days)

        current_week_starts = self._iter_week_starts(period_start, period_end)
        previous_week_starts = self._iter_week_starts(
            prev_period_start, prev_period_end
        )

        if request.report_type == ReportType.STAFF_PERFORMANCE:
            rows = self._build_staff_rows(
                request,
                period_start,
                period_end,
                current_week_starts,
                prev_period_start,
                prev_period_end,
                previous_week_starts,
            )
        else:
            rows = self._build_sales_rows(
                request,
                period_start,
                period_end,
                current_week_starts,
                prev_period_start,
                prev_period_end,
                previous_week_starts,
            )

        return ReportsResponse(
            report_type=request.report_type,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            rows=rows,
        )

    def _build_staff_rows(
        self,
        request: GetReportsRequest,
        period_start,
        period_end,
        current_week_starts: list[str],
        prev_period_start,
        prev_period_end,
        previous_week_starts: list[str],
    ) -> list[dict]:
        current_reports = self._load_waiter_reports(
            current_week_starts, period_start, period_end
        )
        previous_reports = self._load_waiter_reports(
            previous_week_starts,
            prev_period_start,
            prev_period_end,
        )

        if request.location_id is not None:
            current_reports = [
                report
                for report in current_reports
                if report.location_id == request.location_id
            ]
            previous_reports = [
                report
                for report in previous_reports
                if report.location_id == request.location_id
            ]

        current_agg = self._aggregate_waiter_reports(current_reports)
        previous_agg = self._aggregate_waiter_reports(previous_reports)

        keys = sorted(
            current_agg.keys(),
            key=lambda key: (
                (current_agg[key]["location_name"] or "").lower(),
                (current_agg[key]["waiter_last_name"] or "").lower(),
                (current_agg[key]["waiter_first_name"] or "").lower(),
            ),
        )

        rows = []
        for key in keys:
            current = current_agg[key]
            previous = previous_agg.get(key)

            current_avg = self._safe_average(
                current["service_feedback_sum"],
                current["service_feedback_count"],
            )
            previous_avg = (
                self._safe_average(
                    previous["service_feedback_sum"],
                    previous["service_feedback_count"],
                )
                if previous
                else None
            )

            rows.append(
                {
                    "location": current["location_name"],
                    "waiter": (
                        f"{current['waiter_first_name']} {current['waiter_last_name']}"
                    ).strip(),
                    "waiterEmail": current["waiter_email"],
                    "reportPeriodStart": period_start.isoformat(),
                    "reportPeriodEnd": period_end.isoformat(),
                    "waiterWorkingHours": self._format_number(current["working_hours"]),
                    "waiterOrdersProcessed": current["orders_processed"],
                    "deltaWaiterOrdersProcessedPct": self._format_pct(
                        pct_delta(
                            current["orders_processed"],
                            previous["orders_processed"] if previous else None,
                        )
                    ),
                    "averageServiceFeedback": self._format_number(current_avg),
                    "minimumServiceFeedback": self._format_number(
                        current["min_service_feedback"]
                    ),
                    "deltaAverageServiceFeedbackPct": self._format_pct(
                        pct_delta(current_avg, previous_avg)
                    ),
                }
            )

        return rows

    def _build_sales_rows(
        self,
        request: GetReportsRequest,
        period_start,
        period_end,
        current_week_starts: list[str],
        prev_period_start,
        prev_period_end,
        previous_week_starts: list[str],
    ) -> list[dict]:
        current_reports = self._load_location_reports(
            current_week_starts, period_start, period_end
        )
        previous_reports = self._load_location_reports(
            previous_week_starts,
            prev_period_start,
            prev_period_end,
        )

        if request.location_id is not None:
            current_reports = [
                report
                for report in current_reports
                if report.location_id == request.location_id
            ]
            previous_reports = [
                report
                for report in previous_reports
                if report.location_id == request.location_id
            ]

        current_agg = self._aggregate_location_reports(current_reports)
        previous_agg = self._aggregate_location_reports(previous_reports)

        keys = sorted(
            current_agg.keys(),
            key=lambda key: (current_agg[key]["location_name"] or "").lower(),
        )

        rows = []
        for key in keys:
            current = current_agg[key]
            previous = previous_agg.get(key)

            current_avg = self._safe_average(
                current["cuisine_feedback_sum"],
                current["cuisine_feedback_count"],
            )
            previous_avg = (
                self._safe_average(
                    previous["cuisine_feedback_sum"],
                    previous["cuisine_feedback_count"],
                )
                if previous
                else None
            )

            rows.append(
                {
                    "location": current["location_name"],
                    "reportPeriodStart": period_start.isoformat(),
                    "reportPeriodEnd": period_end.isoformat(),
                    "ordersProcessed": current["orders_processed"],
                    "deltaOrdersProcessedPct": self._format_pct(
                        pct_delta(
                            current["orders_processed"],
                            previous["orders_processed"] if previous else None,
                        )
                    ),
                    "averageCuisineFeedback": self._format_number(current_avg),
                    "minimumCuisineFeedback": self._format_number(
                        current["min_cuisine_feedback"]
                    ),
                    "deltaAverageCuisineFeedbackPct": self._format_pct(
                        pct_delta(current_avg, previous_avg)
                    ),
                    "revenue": self._format_number(current["revenue"]),
                    "deltaRevenuePct": self._format_pct(
                        pct_delta(
                            current["revenue"],
                            previous["revenue"] if previous else None,
                        )
                    ),
                }
            )

        return rows

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

    @staticmethod
    def _iter_week_starts(period_start, period_end) -> list[str]:
        """Return ISO-week Monday dates that intersect requested date range."""
        current = period_start_for(period_start)
        last = period_start_for(period_end)
        starts = []
        while current <= last:
            starts.append(current.isoformat())
            current += timedelta(days=7)
        return starts

    @staticmethod
    def _is_report_within_period(report, period_start, period_end) -> bool:
        """Return True when report row overlaps requested date range."""
        report_start = parse_date(report.report_period_start)
        report_end = parse_date(report.report_period_end)
        return report_end >= period_start and report_start <= period_end

    def _load_waiter_reports(self, week_starts, period_start, period_end):
        """Load waiter report rows for requested week starts limited to period overlap."""
        reports = []
        for week_start in week_starts:
            reports.extend(self._waiter_report_repo.find_by_period_start(week_start))
        return [
            report
            for report in reports
            if self._is_report_within_period(report, period_start, period_end)
        ]

    def _load_location_reports(self, week_starts, period_start, period_end):
        """Load location report rows for requested week starts limited to period overlap."""
        reports = []
        for week_start in week_starts:
            reports.extend(self._location_report_repo.find_by_period_start(week_start))
        return [
            report
            for report in reports
            if self._is_report_within_period(report, period_start, period_end)
        ]

    @staticmethod
    def _aggregate_waiter_reports(reports):
        """Aggregate waiter weekly rows into a single row per waiter/location."""
        aggregated = {}
        for report in reports:
            key = (report.location_id, report.waiter_id)
            if key not in aggregated:
                aggregated[key] = {
                    "location_name": report.location_name,
                    "waiter_first_name": report.waiter_first_name,
                    "waiter_last_name": report.waiter_last_name,
                    "waiter_email": report.waiter_email,
                    "working_hours": 0.0,
                    "orders_processed": 0,
                    "service_feedback_count": 0,
                    "service_feedback_sum": 0.0,
                    "min_service_feedback": None,
                }

            row = aggregated[key]
            row["working_hours"] += report.working_hours or 0.0
            row["orders_processed"] += report.orders_processed or 0
            row["service_feedback_count"] += report.service_feedback_count or 0
            row["service_feedback_sum"] += report.service_feedback_sum or 0.0

            report_min = report.min_service_feedback
            if report_min is not None:
                row_min = row["min_service_feedback"]
                row["min_service_feedback"] = (
                    report_min if row_min is None else min(row_min, report_min)
                )

        return aggregated

    @staticmethod
    def _aggregate_location_reports(reports):
        """Aggregate location weekly rows into a single row per location."""
        aggregated = {}
        for report in reports:
            key = report.location_id
            if key not in aggregated:
                aggregated[key] = {
                    "location_name": report.location_name,
                    "orders_processed": 0,
                    "cuisine_feedback_count": 0,
                    "cuisine_feedback_sum": 0.0,
                    "min_cuisine_feedback": None,
                    "revenue": 0.0,
                }

            row = aggregated[key]
            row["orders_processed"] += report.orders_processed or 0
            row["cuisine_feedback_count"] += report.cuisine_feedback_count or 0
            row["cuisine_feedback_sum"] += report.cuisine_feedback_sum or 0.0
            row["revenue"] += report.revenue or 0.0

            report_min = report.min_cuisine_feedback
            if report_min is not None:
                row_min = row["min_cuisine_feedback"]
                row["min_cuisine_feedback"] = (
                    report_min if row_min is None else min(row_min, report_min)
                )

        return aggregated

    @staticmethod
    def _safe_average(total: float, count: int) -> float | None:
        """Return rounded average for sum/count pairs or None when count is zero."""
        if count <= 0:
            return None
        return round(total / count, 2)

    # ------------------------------------------------------------------
    # Report file export
    # ------------------------------------------------------------------

    def export_report_from_payload(self, request: CreateReportsDownloadRequest) -> str:
        """Build a report file from pre-computed rows and return a presigned download URL.

        Args:
            request: Validated request with report metadata, rows, and desired format.

        Returns:
            A temporary presigned URL for downloading the generated file.

        """
        label_map = (
            _STAFF_COLUMN_LABELS
            if request.report_type == ReportType.STAFF_PERFORMANCE
            else _SALES_COLUMN_LABELS
        )
        source_keys = list(label_map.keys())
        header_labels = [label_map[k] for k in source_keys]
        table_rows = [
            [self._to_text(row.get(k, "")) for k in source_keys] for row in request.rows
        ]

        filename_base = (
            f"report_{request.report_type.value}"
            f"_{request.period_start}_{request.period_end}"
        )

        fmt = request.download_format
        if fmt == DownloadFormat.CSV:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(header_labels)
            writer.writerows(table_rows)
            content: bytes = buf.getvalue().encode("utf-8")
            content_type = "text/csv"
            filename = f"{filename_base}.csv"

        elif fmt == DownloadFormat.EXCEL:
            from openpyxl import Workbook  # noqa: PLC0415

            wb = Workbook()
            ws = wb.active
            ws.title = "Report"
            ws.append(header_labels)
            for row in table_rows:
                ws.append(row)
            buf_bytes = io.BytesIO()
            wb.save(buf_bytes)
            content = buf_bytes.getvalue()
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"{filename_base}.xlsx"

        else:  # PDF
            content = self._build_pdf(header_labels, table_rows)
            content_type = "application/pdf"
            filename = f"{filename_base}.pdf"

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        object_key = f"generated-reports/{ts}-{uuid4()}-{filename}"

        self._s3.put_object(
            Bucket=self._settings.reports_bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
            ContentDisposition=f'attachment; filename="{filename}"',
        )

        return self._s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._settings.reports_bucket,
                "Key": object_key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=self._settings.reports_url_expiration_seconds,
        )

    @staticmethod
    def _build_pdf(headers: list[str], rows: list[list[str]]) -> bytes:
        """Render report rows as a PDF table using fpdf2."""
        from fpdf import FPDF  # noqa: PLC0415

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.add_page()

        usable_width = 277.0  # A4 landscape minus default margins
        row_h = 7

        def _fit_text(value: str, width: float) -> str:
            """Trim text so it always fits inside a single PDF cell."""
            if width <= 0:
                return ""
            if pdf.get_string_width(value) <= width:
                return value
            ellipsis = "..."
            if pdf.get_string_width(ellipsis) > width:
                return ""
            trimmed = value
            while trimmed and pdf.get_string_width(trimmed + ellipsis) > width:
                trimmed = trimmed[:-1]
            return (trimmed + ellipsis) if trimmed else ellipsis

        # Compute natural column widths from headers + row values.
        pdf.set_font("Helvetica", "", 7)
        padding = 2.0
        min_col_w = 14.0
        col_widths: list[float] = []
        for idx, header in enumerate(headers):
            max_w = pdf.get_string_width(str(header)) + padding
            for row in rows:
                if idx < len(row):
                    max_w = max(max_w, pdf.get_string_width(str(row[idx])) + padding)
            col_widths.append(max(max_w, min_col_w))

        total_w = sum(col_widths)
        if total_w > usable_width and total_w > 0:
            scale = usable_width / total_w
            col_widths = [w * scale for w in col_widths]

        pdf.set_font("Helvetica", "B", 8)
        for idx, col in enumerate(headers):
            cell_w = col_widths[idx]
            cell_text = _fit_text(str(col), cell_w - 1.0)
            pdf.cell(cell_w, row_h, cell_text, border=1, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for row in rows:
            for idx, val in enumerate(row):
                cell_w = col_widths[idx]
                cell_text = _fit_text(str(val), cell_w - 1.0)
                pdf.cell(cell_w, row_h, cell_text, border=1)
            pdf.ln()

        return bytes(pdf.output())

    @staticmethod
    def _to_text(value: object) -> str:
        """Convert any cell value to a string, returning blank for None."""
        if value is None:
            return ""
        return str(value)

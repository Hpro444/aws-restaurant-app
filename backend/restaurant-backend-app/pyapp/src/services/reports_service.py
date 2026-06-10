"""Service for admin reporting dashboard table data."""

from __future__ import annotations

from datetime import timedelta

from commons.app_config import AppConfig
from commons.report_utils import parse_date, pct_delta, period_start_for
from dto.reports import GetReportsRequest, ReportsResponse, ReportType
from repositories.location_report_repository import LocationReportRepository
from repositories.waiter_report_repository import WaiterReportRepository


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
        self._waiter_report_repo = waiter_report_repo or WaiterReportRepository(cfg)
        self._location_report_repo = location_report_repo or LocationReportRepository(
            cfg
        )

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

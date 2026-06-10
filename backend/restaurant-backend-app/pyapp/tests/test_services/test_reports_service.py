"""Unit tests for ReportsService."""

from unittest import TestCase
from uuid import uuid4

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.location_report import LocationReport
    from domain.waiter_report import WaiterReport
    from dto.reports import GetReportsRequest, ReportType
    from services.reports_service import ReportsService


class _WaiterReportRepo:
    def __init__(self, reports):
        self._reports = reports
        self.calls = []

    def find_by_period_start(self, period_start: str):
        self.calls.append(period_start)
        if isinstance(self._reports, dict):
            return list(self._reports.get(period_start, []))
        return list(self._reports)


class _LocationReportRepo:
    def __init__(self, reports):
        self._reports = reports
        self.calls = []

    def find_by_period_start(self, period_start: str):
        self.calls.append(period_start)
        if isinstance(self._reports, dict):
            return list(self._reports.get(period_start, []))
        return list(self._reports)


class TestReportsService(TestCase):
    """ReportsService formatting and filtering behavior."""

    def test_staff_report_rows_are_built_for_requested_week(self):
        """Build staff rows and compute delta against the previous equal-length period."""
        location_id = uuid4()
        waiter_id = uuid4()
        waiter_report = WaiterReport(
            id=uuid4(),
            waiter_id=waiter_id,
            location_id=location_id,
            location_name="Location 1",
            waiter_first_name="Alex",
            waiter_last_name="Coper",
            waiter_email="alex@example.com",
            report_period_start="2026-06-01",
            report_period_end="2026-06-07",
            working_hours=30.0,
            orders_processed=40,
            service_feedback_count=10,
            service_feedback_sum=45.0,
            avg_service_feedback=4.5,
            min_service_feedback=4,
            orders_processed_delta_pct=None,
            avg_service_feedback_delta_pct=None,
        )
        previous_waiter_report = WaiterReport(
            id=uuid4(),
            waiter_id=waiter_id,
            location_id=location_id,
            location_name="Location 1",
            waiter_first_name="Alex",
            waiter_last_name="Coper",
            waiter_email="alex@example.com",
            report_period_start="2026-05-25",
            report_period_end="2026-05-31",
            working_hours=20.0,
            orders_processed=20,
            service_feedback_count=8,
            service_feedback_sum=32.0,
            avg_service_feedback=4.0,
            min_service_feedback=3,
            orders_processed_delta_pct=None,
            avg_service_feedback_delta_pct=None,
        )

        waiter_repo = _WaiterReportRepo(
            {
                "2026-06-01": [waiter_report],
                "2026-05-25": [previous_waiter_report],
            }
        )
        location_repo = _LocationReportRepo([])
        service = ReportsService(
            waiter_report_repo=waiter_repo,
            location_report_repo=location_repo,
        )

        response = service.get_reports(
            GetReportsRequest(
                reportType="staff_performance",
                periodStart="2026-06-01",
                periodEnd="2026-06-07",
            )
        )

        self.assertEqual(response.report_type, ReportType.STAFF_PERFORMANCE)
        self.assertEqual(response.period_start, "2026-06-01")
        self.assertEqual(response.period_end, "2026-06-07")
        self.assertEqual(len(response.rows), 1)
        self.assertEqual(response.rows[0]["waiter"], "Alex Coper")
        self.assertEqual(response.rows[0]["deltaWaiterOrdersProcessedPct"], "+100%")
        self.assertEqual(response.rows[0]["deltaAverageServiceFeedbackPct"], "+12.5%")

    def test_sales_report_filters_by_location(self):
        """Return only sales rows that match location and compute period-based deltas."""
        location_a = uuid4()
        location_b = uuid4()
        report_a = LocationReport(
            id=uuid4(),
            location_id=location_a,
            location_name="Location A",
            report_period_start="2026-06-01",
            report_period_end="2026-06-07",
            orders_processed=20,
            orders_processed_delta_pct=None,
            cuisine_feedback_count=8,
            cuisine_feedback_sum=32.0,
            avg_cuisine_feedback=4.0,
            min_cuisine_feedback=3,
            avg_cuisine_feedback_delta_pct=None,
            revenue=1200.0,
            revenue_delta_pct=None,
        )
        report_b = LocationReport(
            id=uuid4(),
            location_id=location_b,
            location_name="Location B",
            report_period_start="2026-06-01",
            report_period_end="2026-06-07",
            orders_processed=30,
            orders_processed_delta_pct=None,
            cuisine_feedback_count=7,
            cuisine_feedback_sum=28.0,
            avg_cuisine_feedback=4.0,
            min_cuisine_feedback=3,
            avg_cuisine_feedback_delta_pct=None,
            revenue=900.0,
            revenue_delta_pct=None,
        )
        previous_a = LocationReport(
            id=uuid4(),
            location_id=location_a,
            location_name="Location A",
            report_period_start="2026-05-25",
            report_period_end="2026-05-31",
            orders_processed=10,
            orders_processed_delta_pct=None,
            cuisine_feedback_count=4,
            cuisine_feedback_sum=12.0,
            avg_cuisine_feedback=3.0,
            min_cuisine_feedback=2,
            avg_cuisine_feedback_delta_pct=None,
            revenue=600.0,
            revenue_delta_pct=None,
        )

        waiter_repo = _WaiterReportRepo([])
        location_repo = _LocationReportRepo(
            {
                "2026-06-01": [report_a, report_b],
                "2026-05-25": [previous_a],
            }
        )
        service = ReportsService(
            waiter_report_repo=waiter_repo,
            location_report_repo=location_repo,
        )

        response = service.get_reports(
            GetReportsRequest(
                reportType="sales",
                periodStart="2026-06-01",
                periodEnd="2026-06-07",
                locationId=location_a,
            )
        )

        self.assertEqual(response.report_type, ReportType.SALES)
        self.assertEqual(len(response.rows), 1)
        self.assertEqual(response.rows[0]["location"], "Location A")
        self.assertEqual(response.rows[0]["deltaRevenuePct"], "+100%")

    def test_staff_report_delta_uses_previous_period_same_duration(self):
        """For a 3-week range, compare with the immediately preceding 3-week range."""
        location_id = uuid4()
        waiter_id = uuid4()

        current_reports = [
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-05-18",
                report_period_end="2026-05-24",
                working_hours=10.0,
                orders_processed=10,
                service_feedback_count=2,
                service_feedback_sum=8.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-05-25",
                report_period_end="2026-05-31",
                working_hours=10.0,
                orders_processed=20,
                service_feedback_count=4,
                service_feedback_sum=16.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-06-01",
                report_period_end="2026-06-07",
                working_hours=10.0,
                orders_processed=30,
                service_feedback_count=6,
                service_feedback_sum=24.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
        ]

        previous_reports = [
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-04-27",
                report_period_end="2026-05-03",
                working_hours=10.0,
                orders_processed=10,
                service_feedback_count=2,
                service_feedback_sum=8.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-05-04",
                report_period_end="2026-05-10",
                working_hours=10.0,
                orders_processed=10,
                service_feedback_count=2,
                service_feedback_sum=8.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
            WaiterReport(
                id=uuid4(),
                waiter_id=waiter_id,
                location_id=location_id,
                location_name="Location 1",
                waiter_first_name="Alex",
                waiter_last_name="Coper",
                waiter_email="alex@example.com",
                report_period_start="2026-05-11",
                report_period_end="2026-05-17",
                working_hours=10.0,
                orders_processed=10,
                service_feedback_count=2,
                service_feedback_sum=8.0,
                avg_service_feedback=4.0,
                min_service_feedback=4,
            ),
        ]

        waiter_repo = _WaiterReportRepo(
            {
                "2026-05-18": [current_reports[0]],
                "2026-05-25": [current_reports[1]],
                "2026-06-01": [current_reports[2]],
                "2026-04-27": [previous_reports[0]],
                "2026-05-04": [previous_reports[1]],
                "2026-05-11": [previous_reports[2]],
            }
        )
        service = ReportsService(
            waiter_report_repo=waiter_repo,
            location_report_repo=_LocationReportRepo([]),
        )

        response = service.get_reports(
            GetReportsRequest(
                reportType="staff_performance",
                periodStart="2026-05-18",
                periodEnd="2026-06-07",
                locationId=location_id,
            )
        )

        self.assertEqual(len(response.rows), 1)
        self.assertEqual(response.rows[0]["waiterOrdersProcessed"], 60)
        self.assertEqual(response.rows[0]["deltaWaiterOrdersProcessedPct"], "+100%")

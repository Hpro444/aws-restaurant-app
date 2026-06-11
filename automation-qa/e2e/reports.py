"""E2E suite for the admin-only GET /reports route."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.http_client import execute, skip

ADMIN_EMAIL = "admin@example.com"


def run(ctx) -> None:
    """Exercise both report types, role guards, and period validation."""
    token_admin = ctx.token(ADMIN_EMAIL)
    airport_id = ctx.ids["locations"]["airport"]

    today = datetime.now(UTC).date()
    last_week_monday = (today - timedelta(days=today.weekday() + 7)).isoformat()

    if not token_admin:
        skip(
            ctx,
            step="REP-1",
            name="GET /reports — admin staff-performance report",
            method="GET",
            path="/reports",
            reason=f"no token for {ADMIN_EMAIL} — re-run the seeder to create the admin",
        )
        return

    def _staff_report_check(resp):
        """Assert the staff report echoes its type and returns a rows list."""
        data = resp.json()
        if data.get("reportType") != "staff_performance":
            return False, f"unexpected reportType {data.get('reportType')!r}"
        if not isinstance(data.get("rows"), list):
            return False, "rows is not a list"
        if not data["rows"]:
            return False, "expected seeded staff rows for last week, got none"
        return True, ""

    execute(
        ctx,
        step="REP-1",
        name="GET /reports — staff performance for last week (seeded data)",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={"reportType": "staff_performance", "period": last_week_monday},
        expected=(200,),
        response_check=_staff_report_check,
    )

    execute(
        ctx,
        step="REP-2",
        name="GET /reports — sales report filtered to the Airport location",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={
            "reportType": "sales",
            "period": last_week_monday,
            "locationId": airport_id,
        },
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("reportType") == "sales"
            and isinstance(resp.json().get("rows"), list),
            "expected a sales report with a rows list",
        ),
    )

    execute(
        ctx,
        step="REP-3",
        name="GET /reports — waiter role is forbidden",
        method="GET",
        path="/reports",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        params={"reportType": "staff_performance", "period": last_week_monday},
        expected=(403,),
    )

    execute(
        ctx,
        step="REP-4",
        name="GET /reports — customer role is forbidden",
        method="GET",
        path="/reports",
        token=ctx.token(CUSTOMER_EMAIL),
        auth_user=CUSTOMER_EMAIL,
        params={"reportType": "staff_performance", "period": last_week_monday},
        expected=(403,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="REP-5",
        name="GET /reports — missing period is rejected",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={"reportType": "staff_performance"},
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-6",
        name="GET /reports — invalid reportType is rejected",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={"reportType": "weather", "period": last_week_monday},
        expected=(422,),
    )

    future_monday = (today + timedelta(days=14)).isoformat()
    execute(
        ctx,
        step="REP-7",
        name="GET /reports — future periodStart is rejected",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={"reportType": "staff_performance", "periodStart": future_monday},
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-8",
        name="GET /reports — periodEnd before periodStart is rejected",
        method="GET",
        path="/reports",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        params={
            "reportType": "staff_performance",
            "periodStart": last_week_monday,
            "periodEnd": (today - timedelta(days=30)).isoformat(),
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-9",
        name="GET /reports — missing token is rejected",
        method="GET",
        path="/reports",
        params={"reportType": "staff_performance", "period": last_week_monday},
        expected=(401,),
    )

    # ── POST /reports/download — report file export ───────────────────────────

    last_week_monday_date = today - timedelta(days=today.weekday() + 7)
    period_start = last_week_monday_date.isoformat()
    period_end = (last_week_monday_date + timedelta(days=6)).isoformat()

    _staff_body = {
        "reportType": "staff_performance",
        "periodStart": period_start,
        "periodEnd": period_end,
        "rows": [],
    }
    _sales_body = {
        "reportType": "sales",
        "periodStart": period_start,
        "periodEnd": period_end,
        "rows": [],
    }

    def _has_download_url(resp):
        """Assert the response contains a non-empty https downloadUrl."""
        url = resp.json().get("downloadUrl", "")
        if not url:
            return False, "downloadUrl is missing or empty"
        if not url.startswith("https://"):
            return False, f"downloadUrl is not an https URL: {url!r}"
        return True, ""

    execute(
        ctx,
        step="REP-10",
        name="POST /reports/download?fileFormat=pdf — staff performance PDF",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body=_staff_body,
        expected=(200,),
        response_check=_has_download_url,
    )

    execute(
        ctx,
        step="REP-11",
        name="POST /reports/download?fileFormat=csv — staff performance CSV",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "csv"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body=_staff_body,
        expected=(200,),
        response_check=_has_download_url,
    )

    execute(
        ctx,
        step="REP-12",
        name="POST /reports/download?fileFormat=excel — sales Excel",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "excel"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body=_sales_body,
        expected=(200,),
        response_check=_has_download_url,
    )

    execute(
        ctx,
        step="REP-13",
        name="POST /reports/download — fileFormat=csv supplied in request body",
        method="POST",
        path="/reports/download",
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body={**_staff_body, "fileFormat": "csv"},
        expected=(200,),
        response_check=_has_download_url,
    )

    execute(
        ctx,
        step="REP-14",
        name="POST /reports/download — waiter role is forbidden",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        body=_staff_body,
        expected=(403,),
    )

    execute(
        ctx,
        step="REP-15",
        name="POST /reports/download — customer role is forbidden",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=ctx.token(CUSTOMER_EMAIL),
        auth_user=CUSTOMER_EMAIL,
        body=_staff_body,
        expected=(403,),
    )

    execute(
        ctx,
        step="REP-16",
        name="POST /reports/download — missing token is rejected",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        body=_staff_body,
        expected=(401,),
    )

    execute(
        ctx,
        step="REP-17",
        name="POST /reports/download — missing reportType is rejected",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body={"periodStart": period_start, "periodEnd": period_end, "rows": []},
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-18",
        name="POST /reports/download — invalid reportType is rejected",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body={
            "reportType": "weather",
            "periodStart": period_start,
            "periodEnd": period_end,
            "rows": [],
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-19",
        name="POST /reports/download — periodEnd before periodStart is rejected",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "pdf"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body={
            "reportType": "staff_performance",
            "periodStart": period_end,
            "periodEnd": period_start,
            "rows": [],
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="REP-20",
        name="POST /reports/download?fileFormat=xml — invalid format is rejected",
        method="POST",
        path="/reports/download",
        params={"fileFormat": "xml"},
        token=token_admin,
        auth_user=ADMIN_EMAIL,
        body=_staff_body,
        expected=(422,),
    )

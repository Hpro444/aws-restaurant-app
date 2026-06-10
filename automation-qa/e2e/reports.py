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

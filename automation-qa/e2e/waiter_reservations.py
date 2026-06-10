"""E2E suite for the GET /reservations/waiter table-view endpoint."""

from __future__ import annotations

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.http_client import execute, skip


def run(ctx) -> None:
    """Verify max sees kate's reservation on his table view and the role guard."""
    res_id = ctx.state.get("res_id_a")
    booking_date = ctx.state.get("booking_date")
    if not res_id or not booking_date:
        skip(
            ctx,
            step="WRES-1",
            name="GET /reservations/waiter — table view",
            method="GET",
            path="/reservations/waiter",
            reason="no reservation available from the bookings suite",
        )
        return

    params = {"date": booking_date, "time_from": "00:00", "table_name": "1"}

    execute(
        ctx,
        step="WRES-1",
        name="GET /reservations/waiter — max's view of Airport table 1",
        method="GET",
        path="/reservations/waiter",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        params=params,
        expected=(200,),
        response_check=lambda resp: (
            any(
                r.get("reservationId") == res_id
                for r in resp.json().get("reservations", [])
            ),
            f"reservation {res_id} not present in waiter table view",
        ),
    )

    execute(
        ctx,
        step="WRES-2",
        name="GET /reservations/waiter — customer role is forbidden",
        method="GET",
        path="/reservations/waiter",
        token=ctx.token(CUSTOMER_EMAIL),
        auth_user=CUSTOMER_EMAIL,
        params=params,
        expected=(403,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="WRES-3",
        name="GET /reservations/waiter — missing table_name is rejected",
        method="GET",
        path="/reservations/waiter",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        params={"date": booking_date, "time_from": "00:00"},
        expected=(422,),
    )

    execute(
        ctx,
        step="WRES-4",
        name="GET /reservations/waiter — malformed time_from is rejected",
        method="GET",
        path="/reservations/waiter",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        params={"date": booking_date, "time_from": "9am", "table_name": "1"},
        expected=(422,),
    )

    execute(
        ctx,
        step="WRES-5",
        name="GET /reservations/waiter — malformed date is rejected",
        method="GET",
        path="/reservations/waiter",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        params={"date": "tomorrow", "time_from": "00:00", "table_name": "1"},
        expected=(422,),
    )

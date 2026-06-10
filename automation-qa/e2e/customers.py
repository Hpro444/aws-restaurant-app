"""E2E suite for the /customers route group."""

from __future__ import annotations

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import count_items, make_check
from e2e.http_client import execute


def run(ctx) -> None:
    """Exercise the waiter-only customers list and its role guard."""

    def _customers_db_check(resp):
        """Compare the returned customer count with the customers table."""
        api_count = len(resp.json())
        db_count = count_items(ctx.table("customers"))
        return [
            make_check(
                "customers",
                "API customer count equals table item count (read-only)",
                api_count == db_count,
                before=f"table rows: {db_count}",
                after=f"API returned: {api_count}",
            )
        ]

    execute(
        ctx,
        step="CUST-1",
        name="GET /customers — waiter lists all customers",
        method="GET",
        path="/customers",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        expected=(200,),
        db_check=_customers_db_check,
    )

    execute(
        ctx,
        step="CUST-2",
        name="GET /customers — customer role is forbidden",
        method="GET",
        path="/customers",
        token=ctx.token(CUSTOMER_EMAIL),
        auth_user=CUSTOMER_EMAIL,
        expected=(403,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="CUST-3",
        name="GET /customers — missing token is rejected",
        method="GET",
        path="/customers",
        expected=(401,),
    )

"""E2E suite for the /orders route group."""

from __future__ import annotations

import uuid

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import make_check, scan_eq, wait_until
from e2e.http_client import execute, skip


def run(ctx) -> None:
    """Create an order on the in-progress reservation and check the role guard."""
    res_id = ctx.state.get("res_id_a")
    if not res_id:
        skip(
            ctx,
            step="ORD-1",
            name="POST /orders — waiter creates an order",
            method="POST",
            path="/orders",
            reason="no reservation available from the bookings suite",
        )
        return

    wrap_dish_id = ctx.ids["dishes"]["airport"]["Grilled Chicken Wrap"]
    orders_tbl = ctx.table("orders")

    def _order_db_check(resp):
        """Verify an orders row was written for the reservation."""
        order_id = resp.json().get("orderId")
        appeared = wait_until(
            lambda: len(scan_eq(orders_tbl, reservation_id=res_id)) >= 1
        )
        rows = scan_eq(orders_tbl, reservation_id=res_id)
        id_match = any(r.get("id") == order_id for r in rows)
        return [
            make_check(
                "orders",
                f"row created for reservation (orderId={order_id})",
                appeared and id_match,
                before="0 rows for this reservation",
                after=f"{len(rows)} row(s); items={rows[0].get('items') if rows else None}",
            )
        ]

    execute(
        ctx,
        step="ORD-1",
        name="POST /orders — max orders 2x Grilled Chicken Wrap",
        method="POST",
        path="/orders",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        body={
            "reservationId": res_id,
            "items": [{"dishId": wrap_dish_id, "quantity": 2}],
        },
        expected=(201,),
        db_check=_order_db_check,
    )

    execute(
        ctx,
        step="ORD-2",
        name="POST /orders — customer role is forbidden",
        method="POST",
        path="/orders",
        token=ctx.token(CUSTOMER_EMAIL),
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservationId": res_id,
            "items": [{"dishId": wrap_dish_id, "quantity": 1}],
        },
        expected=(403,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    token_max = ctx.token(WAITER_EMAIL)

    execute(
        ctx,
        step="ORD-3",
        name="POST /orders — missing items is rejected",
        method="POST",
        path="/orders",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={"reservationId": res_id},
        expected=(422,),
    )

    execute(
        ctx,
        step="ORD-4",
        name="POST /orders — empty items list is rejected",
        method="POST",
        path="/orders",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={"reservationId": res_id, "items": []},
        expected=(422,),
    )

    execute(
        ctx,
        step="ORD-5",
        name="POST /orders — zero quantity is rejected",
        method="POST",
        path="/orders",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={
            "reservationId": res_id,
            "items": [{"dishId": wrap_dish_id, "quantity": 0}],
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="ORD-6",
        name="POST /orders — unknown dishId returns 404",
        method="POST",
        path="/orders",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={
            "reservationId": res_id,
            "items": [{"dishId": str(uuid.uuid4()), "quantity": 1}],
        },
        expected=(404,),
    )

    execute(
        ctx,
        step="ORD-7",
        name="POST /orders — unknown reservationId returns 404",
        method="POST",
        path="/orders",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={
            "reservationId": str(uuid.uuid4()),
            "items": [{"dishId": wrap_dish_id, "quantity": 1}],
        },
        expected=(404,),
    )

    execute(
        ctx,
        step="ORD-8",
        name="POST /orders — non-assigned waiter (lea) is forbidden",
        method="POST",
        path="/orders",
        token=ctx.token("lea@example.com"),
        auth_user="lea@example.com",
        body={
            "reservationId": res_id,
            "items": [{"dishId": wrap_dish_id, "quantity": 1}],
        },
        expected=(403,),
    )

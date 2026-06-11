"""E2E suite for SQS-triggered report recalculations (T-1 through T-12).

Exercises the full reservation lifecycle at Airport table 1 (day-after-
tomorrow, to avoid slot conflicts with the bookings suite) and verifies that
each SQS-triggering event — reservation FINISHED, culinary / service feedback
created, duplicate rejected, and feedback edited — recalculates the
``waiter_report`` and ``location_report`` aggregates within 15 seconds.

This suite is the e2e-integrated equivalent of ``backend/test_sqs_endpoints.py``.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from boto3.dynamodb.conditions import Key

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import dec_to_native, make_check, wait_until
from e2e.http_client import execute, skip

_SQS_TIMEOUT = 15.0
_UNCHANGED_WAIT = 3.0

_WAITER_FIELDS = ["orders_processed", "service_feedback_count", "avg_service_feedback"]
_LOCATION_FIELDS = [
    "orders_processed",
    "revenue",
    "cuisine_feedback_count",
    "avg_cuisine_feedback",
]


# ── Report-table GSI helpers ──────────────────────────────────────────────────


def _snap_waiter_report(table, waiter_id: str, period_start: str) -> dict | None:
    """Query waiter_period_index GSI and return the current row, or None."""
    if table is None:
        return None
    resp = table.query(
        IndexName="waiter_period_index",
        KeyConditionExpression=(
            Key("waiter_id").eq(waiter_id) & Key("report_period_start").eq(period_start)
        ),
        Limit=1,
    )
    items = resp.get("Items", [])
    return dec_to_native(items[0]) if items else None


def _snap_location_report(table, location_id: str, period_start: str) -> dict | None:
    """Query location_period_index GSI and return the current row, or None."""
    if table is None:
        return None
    resp = table.query(
        IndexName="location_period_index",
        KeyConditionExpression=(
            Key("location_id").eq(location_id)
            & Key("report_period_start").eq(period_start)
        ),
        Limit=1,
    )
    items = resp.get("Items", [])
    return dec_to_native(items[0]) if items else None


# ── Assertion helpers ─────────────────────────────────────────────────────────


def _row_summary(row: dict | None, fields: list[str]) -> str:
    """Format selected fields of a row as a one-line string."""
    if row is None:
        return "(no row)"
    return ", ".join(f"{f}={row.get(f)!r}" for f in fields)


def _fields_unchanged(snap_fn, before: dict | None, fields: list[str]) -> bool:
    """Return True if none of the tracked fields changed from ``before``."""
    current = snap_fn()
    if before is None and current is None:
        return True
    if before is None or current is None:
        return False
    return all(current.get(f) == before.get(f) for f in fields)


def _unchanged_check(
    snap_fn, before: dict | None, fields: list[str], table_alias: str, expectation: str
) -> list:
    """Sleep briefly, then assert the tracked fields are still equal to ``before``."""
    time.sleep(_UNCHANGED_WAIT)
    return [
        make_check(
            table_alias,
            expectation,
            _fields_unchanged(snap_fn, before, fields),
            before=_row_summary(before, fields),
            after=_row_summary(snap_fn(), fields),
        )
    ]


def _increased_check(
    snap_fn, before: dict | None, field: str, table_alias: str, expectation: str
) -> list:
    """Poll until ``field`` is strictly greater than its value in ``before``, then record the check."""
    changed = wait_until(
        lambda: (snap_fn() or {}).get(field, 0) > (before or {}).get(field, 0),
        timeout=_SQS_TIMEOUT,
    )
    return [
        make_check(
            table_alias,
            expectation,
            changed,
            before=_row_summary(before, [field]),
            after=_row_summary(snap_fn(), [field]),
        )
    ]


def _decreased_check(
    snap_fn, before: dict | None, field: str, table_alias: str, expectation: str
) -> list:
    """Poll until ``field`` is strictly less than its value in ``before``, then record the check."""
    before_val = float((before or {}).get(field) or 5)

    def _predicate():
        """Return True when the field has dropped below the baseline."""
        current = snap_fn()
        current_val = (current or {}).get(field)
        if current_val is None:
            return False
        return float(current_val) < before_val

    changed = wait_until(_predicate, timeout=_SQS_TIMEOUT)
    return [
        make_check(
            table_alias,
            expectation,
            changed,
            before=_row_summary(before, [field]),
            after=_row_summary(snap_fn(), [field]),
        )
    ]


# ── Suite entry point ─────────────────────────────────────────────────────────


def run(ctx) -> None:
    """Run T-1 through T-12: full SQS-triggered report recalculation lifecycle."""
    airport_id = ctx.ids["locations"]["airport"]
    max_waiter_id = ctx.ids["waiters"][WAITER_EMAIL]

    try:
        airport_dish_id = ctx.ids["dishes"]["airport"]["Grilled Chicken Wrap"]
    except (KeyError, TypeError):
        airport_dish_id = None

    token_kate = ctx.token(CUSTOMER_EMAIL)
    token_max = ctx.token(WAITER_EMAIL)

    waiter_report_tbl = ctx.table("waiter_report")
    location_report_tbl = ctx.table("location_report")

    # Day-after-tomorrow avoids slot conflicts with the bookings suite (tomorrow).
    booking_date = (datetime.now(UTC).date() + timedelta(days=2)).isoformat()
    date_obj = datetime.fromisoformat(booking_date).date()
    period_start = (date_obj - timedelta(days=date_obj.weekday())).isoformat()

    def snap_waiter() -> dict | None:
        """Return a fresh waiter-report snapshot for max, this ISO week."""
        return _snap_waiter_report(waiter_report_tbl, max_waiter_id, period_start)

    def snap_location() -> dict | None:
        """Return a fresh location-report snapshot for Airport, this ISO week."""
        return _snap_location_report(location_report_tbl, airport_id, period_start)

    # ── SQS-0: discover 2 free Airport table-1 slots on booking_date ─────────

    slot_a: dict | None = None
    slot_b: dict | None = None

    def _capture_slots(resp):
        """Pick the first two available slots at Airport table 1."""
        nonlocal slot_a, slot_b
        table1 = next(
            (t for t in resp.json().get("tables", []) if t.get("table_number") == 1),
            None,
        )
        if table1 is None:
            return False, "Airport table 1 not found in availability response"
        available = table1.get("available_slots", [])
        if len(available) < 2:
            return False, f"need >= 2 free slots at table 1, found {len(available)}"
        slot_a = available[0]
        slot_b = available[1]
        return True, ""

    execute(
        ctx,
        step="SQS-0",
        name=f"GET /bookings/tables — discover 2 free slots at Airport table 1 ({booking_date})",
        method="GET",
        path="/bookings/tables",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        params={"location_id": airport_id, "date": booking_date, "guests_number": 2},
        expected=(200,),
        response_check=_capture_slots,
    )

    _later_steps = [
        ("SQS-1", "POST /bookings/client — slot A", "POST", "/bookings/client"),
        (
            "SQS-2",
            "PUT /bookings/waiter/{id} — IN_PROGRESS",
            "PUT",
            "/bookings/waiter/{id}",
        ),
        ("SQS-3", "POST /orders", "POST", "/orders"),
        (
            "SQS-4",
            "PUT /bookings/waiter/{id} — FINISHED",
            "PUT",
            "/bookings/waiter/{id}",
        ),
        ("SQS-5", "POST /feedbacks — culinary", "POST", "/feedbacks"),
        ("SQS-6", "POST /feedbacks — service", "POST", "/feedbacks"),
        ("SQS-7", "POST /feedbacks — duplicate culinary → 409", "POST", "/feedbacks"),
        ("SQS-8", "POST /feedbacks — duplicate service → 409", "POST", "/feedbacks"),
        ("SQS-9", "POST /bookings/client — slot B", "POST", "/bookings/client"),
        (
            "SQS-10",
            "DELETE /bookings/client/{id}/cancel",
            "DELETE",
            "/bookings/client/{id}/cancel",
        ),
        ("SQS-11", "PUT /feedbacks — service edit 4→1", "PUT", "/feedbacks"),
        ("SQS-12", "PUT /feedbacks — culinary edit 5→1", "PUT", "/feedbacks"),
    ]

    if slot_a is None or slot_b is None:
        reason = f"SQS-0 failed to find 2 free slots on {booking_date}"
        for step, name, method, path in _later_steps:
            skip(ctx, step=step, name=name, method=method, path=path, reason=reason)
        return

    # ── T-1: kate creates reservation (slot A) ─────────────────────────────────
    #         SQS CREATED — ignored by both report services.

    res_id: str | None = None

    def _capture_res_id(resp):
        """Store the reservation ID for subsequent steps."""
        nonlocal res_id
        data = resp.json()
        res_id = data.get("reservationId") or data.get("id")
        if not res_id:
            return False, "no reservationId in response body"
        return True, ""

    bw1 = snap_waiter()
    bl1 = snap_location()

    execute(
        ctx,
        step="SQS-1",
        name="POST /bookings/client — kate creates reservation (slot A); SQS CREATED → reports unchanged",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "locationId": airport_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_a["start_time"],
            "timeTo": slot_a["end_time"],
        },
        expected=(200, 201),
        response_check=_capture_res_id,
        db_check=lambda _resp, bw=bw1, bl=bl1: (
            _unchanged_check(
                snap_waiter,
                bw,
                _WAITER_FIELDS,
                "waiter_report",
                "CREATED ignored — waiter report unchanged",
            )
            + _unchanged_check(
                snap_location,
                bl,
                _LOCATION_FIELDS,
                "location_report",
                "CREATED ignored — location report unchanged",
            )
        ),
    )

    if not res_id:
        reason = "SQS-1 did not return a reservationId"
        for step, name, method, path in _later_steps[1:]:
            skip(ctx, step=step, name=name, method=method, path=path, reason=reason)
        return

    # ── T-2: max moves RESERVED → IN_PROGRESS ──────────────────────────────────
    #         SQS UPDATED — ignored by both report services.

    bw2 = snap_waiter()
    bl2 = snap_location()

    execute(
        ctx,
        step="SQS-2",
        name="PUT /bookings/waiter/{id} — max moves reservation IN_PROGRESS; SQS UPDATED → reports unchanged",
        method="PUT",
        path=f"/bookings/waiter/{res_id}",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={"status": "In Progress"},
        expected=(200,),
        db_check=lambda _resp, bw=bw2, bl=bl2: (
            _unchanged_check(
                snap_waiter,
                bw,
                _WAITER_FIELDS,
                "waiter_report",
                "UPDATED ignored — waiter report unchanged",
            )
            + _unchanged_check(
                snap_location,
                bl,
                _LOCATION_FIELDS,
                "location_report",
                "UPDATED ignored — location report unchanged",
            )
        ),
    )

    # ── T-3: max creates an order (no SQS; revenue counted at FINISHED) ────────

    if airport_dish_id:
        execute(
            ctx,
            step="SQS-3",
            name="POST /orders — max creates order (2× Grilled Chicken Wrap); no SQS, revenue counted at FINISHED",
            method="POST",
            path="/orders",
            token=token_max,
            auth_user=WAITER_EMAIL,
            body={
                "reservationId": res_id,
                "items": [{"dishId": airport_dish_id, "quantity": 2}],
            },
            expected=(200, 201),
        )
    else:
        skip(
            ctx,
            step="SQS-3",
            name="POST /orders — create order",
            method="POST",
            path="/orders",
            reason="Grilled Chicken Wrap id not found in ids.json",
        )

    # ── T-4: max marks reservation FINISHED ────────────────────────────────────
    #         SQS FINISHED → waiter-report + location-report recalculated.

    bw4 = snap_waiter()
    bl4 = snap_location()

    def _db_check_t4(_resp, bw=bw4, bl=bl4):
        """Assert orders_processed increased in both reports and revenue increased in location."""
        checks = []
        checks += _increased_check(
            snap_waiter,
            bw,
            "orders_processed",
            "waiter_report",
            "orders_processed increased after FINISHED",
        )
        checks += _increased_check(
            snap_location,
            bl,
            "orders_processed",
            "location_report",
            "orders_processed increased after FINISHED",
        )
        checks += _increased_check(
            snap_location,
            bl,
            "revenue",
            "location_report",
            "revenue increased after FINISHED",
        )
        return checks

    execute(
        ctx,
        step="SQS-4",
        name="PUT /bookings/waiter/{id} — max marks FINISHED; SQS FINISHED → orders_processed+1, revenue+",
        method="PUT",
        path=f"/bookings/waiter/{res_id}",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={"status": "Finished"},
        expected=(200,),
        db_check=_db_check_t4,
    )

    # ── T-5: kate submits CULINARY feedback (rating 5) ─────────────────────────
    #         SQS CULINARY CREATED → location-report cuisine_feedback_count +1.

    bl5 = snap_location()

    execute(
        ctx,
        step="SQS-5",
        name="POST /feedbacks — kate submits culinary feedback (rate 5); SQS CULINARY CREATED → cuisine_feedback_count+1",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "Excellent flavors and beautifully presented.",
            "rating": 5,
            "type": "culinary",
        },
        expected=(201,),
        db_check=lambda _resp, bl=bl5: _increased_check(
            snap_location,
            bl,
            "cuisine_feedback_count",
            "location_report",
            "cuisine_feedback_count increased after culinary feedback",
        ),
    )

    # ── T-6: kate submits SERVICE feedback (rating 4) ──────────────────────────
    #         SQS SERVICE CREATED → waiter-report service_feedback_count +1.

    bw6 = snap_waiter()

    execute(
        ctx,
        step="SQS-6",
        name="POST /feedbacks — kate submits service feedback (rate 4); SQS SERVICE CREATED → service_feedback_count+1",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "Attentive and professional throughout the visit.",
            "rating": 4,
            "type": "service",
        },
        expected=(201,),
        db_check=lambda _resp, bw=bw6: _increased_check(
            snap_waiter,
            bw,
            "service_feedback_count",
            "waiter_report",
            "service_feedback_count increased after service feedback",
        ),
    )

    # ── T-7: duplicate CULINARY → 409 (rejected before SQS publish) ────────────

    bl7 = snap_location()

    execute(
        ctx,
        step="SQS-7",
        name="POST /feedbacks — duplicate culinary → 409; no SQS, location report unchanged",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "Trying a second culinary rating.",
            "rating": 3,
            "type": "culinary",
        },
        expected=(409,),
        db_check=lambda _resp, bl=bl7: _unchanged_check(
            snap_location,
            bl,
            _LOCATION_FIELDS,
            "location_report",
            "location report unchanged after rejected duplicate",
        ),
    )

    # ── T-8: duplicate SERVICE → 409 (rejected before SQS publish) ─────────────

    bw8 = snap_waiter()

    execute(
        ctx,
        step="SQS-8",
        name="POST /feedbacks — duplicate service → 409; no SQS, waiter report unchanged",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "Trying a second service rating.",
            "rating": 5,
            "type": "service",
        },
        expected=(409,),
        db_check=lambda _resp, bw=bw8: _unchanged_check(
            snap_waiter,
            bw,
            _WAITER_FIELDS,
            "waiter_report",
            "waiter report unchanged after rejected duplicate",
        ),
    )

    # ── T-9: kate creates a 2nd reservation (slot B) ───────────────────────────
    #         SQS CREATED — ignored by both report services.

    res_id_b: str | None = None

    def _capture_res_id_b(resp):
        """Capture the second reservation ID for the cancellation step."""
        nonlocal res_id_b
        data = resp.json()
        res_id_b = data.get("reservationId") or data.get("id")
        if not res_id_b:
            return False, "no reservationId in response body"
        return True, ""

    bl9 = snap_location()

    execute(
        ctx,
        step="SQS-9",
        name="POST /bookings/client — kate creates reservation (slot B); SQS CREATED → location report unchanged",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "locationId": airport_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_b["start_time"],
            "timeTo": slot_b["end_time"],
        },
        expected=(200, 201),
        response_check=_capture_res_id_b,
        db_check=lambda _resp, bl=bl9: _unchanged_check(
            snap_location,
            bl,
            _LOCATION_FIELDS,
            "location_report",
            "CREATED ignored — location report unchanged",
        ),
    )

    # ── T-10: kate cancels the 2nd reservation ─────────────────────────────────
    #          SQS CANCELLED — ignored by both report services.

    if not res_id_b:
        skip(
            ctx,
            step="SQS-10",
            name="DELETE /bookings/client/{id}/cancel — kate cancels slot B",
            method="DELETE",
            path="/bookings/client/{id}/cancel",
            reason="SQS-9 did not return a reservationId",
        )
    else:
        bl10 = snap_location()

        execute(
            ctx,
            step="SQS-10",
            name="DELETE /bookings/client/{id}/cancel — kate cancels slot B; SQS CANCELLED → reports unchanged",
            method="DELETE",
            path=f"/bookings/client/{res_id_b}/cancel",
            token=token_kate,
            auth_user=CUSTOMER_EMAIL,
            expected=(200, 204),
            db_check=lambda _resp, bl=bl10: _unchanged_check(
                snap_location,
                bl,
                _LOCATION_FIELDS,
                "location_report",
                "CANCELLED ignored — location report unchanged",
            ),
        )

    # ── T-11: kate edits SERVICE feedback (4 → 1) ──────────────────────────────
    #          SQS SERVICE EDITED → waiter-report recalculated, avg_service_feedback drops.

    bw11 = snap_waiter()

    execute(
        ctx,
        step="SQS-11",
        name="PUT /feedbacks — kate edits service feedback 4→1; SQS SERVICE EDITED → avg_service_feedback drops",
        method="PUT",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "On reflection the service was slow.",
            "rating": 1,
            "type": "service",
        },
        expected=(200,),
        db_check=lambda _resp, bw=bw11: _decreased_check(
            snap_waiter,
            bw,
            "avg_service_feedback",
            "waiter_report",
            "avg_service_feedback decreased after service feedback edit",
        ),
    )

    # ── T-12: kate edits CULINARY feedback (5 → 1) ─────────────────────────────
    #          SQS CULINARY EDITED → location-report recalculated, avg_cuisine_feedback drops.

    bl12 = snap_location()

    execute(
        ctx,
        step="SQS-12",
        name="PUT /feedbacks — kate edits culinary feedback 5→1; SQS CULINARY EDITED → avg_cuisine_feedback drops",
        method="PUT",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "comment": "On reflection the food was disappointing.",
            "rating": 1,
            "type": "culinary",
        },
        expected=(200,),
        db_check=lambda _resp, bl=bl12: _decreased_check(
            snap_location,
            bl,
            "avg_cuisine_feedback",
            "location_report",
            "avg_cuisine_feedback decreased after culinary feedback edit",
        ),
    )

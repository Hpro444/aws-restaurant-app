"""E2E suite finishing the primary reservation and exercising cancellation."""

from __future__ import annotations

import uuid

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import get_by_id, make_check, row_summary, wait_until
from e2e.http_client import execute, skip


def run(ctx) -> None:
    """Finish reservation A (enables feedback) and create+cancel reservation B."""
    airport_id = ctx.ids["locations"]["airport"]
    token_kate = ctx.token(CUSTOMER_EMAIL)
    token_max = ctx.token(WAITER_EMAIL)
    reservations_tbl = ctx.table("reservations")
    res_id = ctx.state.get("res_id_a")
    slot_b = ctx.state.get("slot_b")
    booking_date = ctx.state.get("booking_date")

    if not res_id:
        skip(
            ctx,
            step="LIFE-1",
            name="PUT /bookings/waiter/{id} — finish reservation",
            method="PUT",
            path="/bookings/waiter/{id}",
            reason="no reservation available from the bookings suite",
        )
    else:

        def _finish_db_check(_resp):
            """Verify status moved to 'Finished' in DynamoDB."""
            changed = wait_until(
                lambda: (
                    (get_by_id(reservations_tbl, res_id) or {}).get("status")
                    == "Finished"
                )
            )
            after_row = get_by_id(reservations_tbl, res_id)
            return [
                make_check(
                    "reservations",
                    "status updated 'In Progress' -> 'Finished'",
                    changed,
                    before="status='In Progress'",
                    after=row_summary(after_row, ["status", "number_of_guests"]),
                )
            ]

        execute(
            ctx,
            step="LIFE-1",
            name="PUT /bookings/waiter/{id} — max finishes the reservation",
            method="PUT",
            path=f"/bookings/waiter/{res_id}",
            token=token_max,
            auth_user=WAITER_EMAIL,
            body={"status": "Finished"},
            expected=(200,),
            db_check=_finish_db_check,
        )

    if not slot_b or not booking_date:
        skip(
            ctx,
            step="LIFE-2",
            name="POST /bookings/client — second booking",
            method="POST",
            path="/bookings/client",
            reason="no free slot B discovered in the bookings suite",
        )
        skip(
            ctx,
            step="LIFE-3",
            name="DELETE /bookings/client/{id}/cancel",
            method="DELETE",
            path="/bookings/client/{id}/cancel",
            reason="no second booking to cancel",
        )
    else:

        def _capture_second(resp):
            """Store the second reservation id for the cancel step."""
            res_id_b = resp.json().get("reservationId") or resp.json().get("id")
            if not res_id_b:
                return False, "response missing reservationId"
            ctx.state["res_id_b"] = res_id_b
            return True, ""

        def _second_db_check(resp):
            """Verify the second reservation row was written."""
            res_id_b = resp.json().get("reservationId") or resp.json().get("id")
            appeared = wait_until(
                lambda: get_by_id(reservations_tbl, res_id_b) is not None
            )
            row = get_by_id(reservations_tbl, res_id_b)
            return [
                make_check(
                    "reservations",
                    "second row created with status='Reserved'",
                    appeared and bool(row) and row.get("status") == "Reserved",
                    before="(no row)",
                    after=row_summary(row, ["status", "number_of_guests", "date"]),
                )
            ]

        execute(
            ctx,
            step="LIFE-2",
            name="POST /bookings/client — kate books slot B",
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
            response_check=_capture_second,
            db_check=_second_db_check,
        )

        res_id_b = ctx.state.get("res_id_b")
        if not res_id_b:
            skip(
                ctx,
                step="LIFE-3",
                name="DELETE /bookings/client/{id}/cancel",
                method="DELETE",
                path="/bookings/client/{id}/cancel",
                reason="no second booking to cancel",
            )
        else:

            def _cancel_db_check(_resp):
                """Verify the second reservation row is now Cancelled."""
                changed = wait_until(
                    lambda: (
                        (get_by_id(reservations_tbl, res_id_b) or {}).get("status")
                        == "Cancelled"
                    )
                )
                after_row = get_by_id(reservations_tbl, res_id_b)
                return [
                    make_check(
                        "reservations",
                        "status updated 'Reserved' -> 'Cancelled'",
                        changed,
                        before="status='Reserved'",
                        after=row_summary(after_row, ["status"]),
                    )
                ]

            execute(
                ctx,
                step="LIFE-3",
                name="DELETE /bookings/client/{id}/cancel — kate cancels slot B",
                method="DELETE",
                path=f"/bookings/client/{res_id_b}/cancel",
                token=token_kate,
                auth_user=CUSTOMER_EMAIL,
                expected=(200, 204),
                db_check=_cancel_db_check,
            )

    execute(
        ctx,
        step="LIFE-4",
        name="GET /bookings/client/{id} — unknown reservation returns 404",
        method="GET",
        path=f"/bookings/client/{uuid.uuid4()}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(404,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="LIFE-5",
        name="DELETE /bookings/client/{id}/cancel — unknown reservation returns 404",
        method="DELETE",
        path=f"/bookings/client/{uuid.uuid4()}/cancel",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(404,),
    )

    execute(
        ctx,
        step="LIFE-6",
        name="DELETE /bookings/client/{id}/cancel — malformed UUID is rejected",
        method="DELETE",
        path="/bookings/client/not-a-uuid/cancel",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(422,),
    )

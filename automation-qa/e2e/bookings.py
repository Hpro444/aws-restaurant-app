"""E2E suite for booking availability, creation, reads, and updates.

Creates the primary reservation (kate at Airport table 1, tomorrow) that the
orders, waiter_reservations, bookings_lifecycle, and feedbacks suites reuse
via ``ctx.state``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import get_by_id, make_check, row_summary, wait_until
from e2e.http_client import execute, skip


def run(ctx) -> None:
    """Exercise both availability endpoints and the client booking lifecycle."""
    airport_id = ctx.ids["locations"]["airport"]
    max_waiter_id = ctx.ids["waiters"][WAITER_EMAIL]
    token_kate = ctx.token(CUSTOMER_EMAIL)
    token_max = ctx.token(WAITER_EMAIL)
    reservations_tbl = ctx.table("reservations")
    slots_tbl = ctx.table("slots")

    booking_date = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    ctx.state["booking_date"] = booking_date

    def _capture_slots(resp):
        """Pick two seed-safe, DB-verified FREE slots at Airport table 1.

        The seeder books the two earliest slots of every waiter for each of
        the next six days (current-week FINISHED report data), so the first
        windows listed by the availability endpoint are not guaranteed to be
        bookable.  Every candidate is therefore verified against the slots
        base table: only rows that are truly status=FREE and assigned to max
        (the first-shift table-1 waiter the rest of the suite relies on) are
        used.  Mismatches are kept for the BOOK-1 DB cross-check.
        """
        table1 = next(
            (t for t in resp.json().get("tables", []) if t.get("table_number") == 1),
            None,
        )
        if table1 is None:
            return False, "Airport table 1 missing from availability response"
        listed = table1.get("available_slots", [])
        ctx.state["slots_listed_count"] = len(listed)

        verified, mismatched = [], []
        for cand in listed:
            row = get_by_id(slots_tbl, cand.get("slot_id"))
            if row is None:
                mismatched.append(f"{cand.get('start_time')}: no row in slots table")
            elif row.get("status") != "FREE":
                mismatched.append(
                    f"{cand.get('start_time')}: listed available but status={row.get('status')!r}"
                )
            elif str(row.get("waiter_id")) != str(max_waiter_id):
                continue  # other shift's waiter — valid slot, just not usable here
            else:
                verified.append(cand)
        ctx.state["slot_mismatches"] = mismatched

        if len(verified) < 2:
            return False, (
                f"need >= 2 DB-verified FREE slots for max at table 1, found "
                f"{len(verified)} ({len(mismatched)} mismatched with slots table)"
            )
        ctx.state["slot_a"] = verified[0]
        ctx.state["slot_b"] = verified[1]
        return True, ""

    def _availability_db_check(_resp):
        """Cross-check that every slot listed as available is FREE in DynamoDB."""
        mismatched = ctx.state.get("slot_mismatches", [])
        listed = ctx.state.get("slots_listed_count", 0)
        return [
            make_check(
                "slots",
                "every availability-listed slot is status=FREE in the slots table",
                not mismatched,
                before=f"{listed} slots listed by the API",
                after=(
                    "all verified FREE"
                    if not mismatched
                    else f"{len(mismatched)} mismatch(es): " + "; ".join(mismatched)
                ),
            )
        ]

    execute(
        ctx,
        step="BOOK-1",
        name=f"GET /bookings/tables — availability for Airport on {booking_date}",
        method="GET",
        path="/bookings/tables",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        params={
            "location_id": airport_id,
            "date": booking_date,
            "guests_number": 2,
        },
        expected=(200,),
        response_check=_capture_slots,
        db_check=_availability_db_check,
    )

    slot_a = ctx.state.get("slot_a")
    slot_b = ctx.state.get("slot_b")
    if not slot_a or not slot_b:
        for step, name, method, path in [
            ("BOOK-2", "GET /bookings/waiter/tables", "GET", "/bookings/waiter/tables"),
            ("BOOK-3", "POST /bookings/client", "POST", "/bookings/client"),
            ("BOOK-4", "GET /bookings/client", "GET", "/bookings/client"),
            ("BOOK-5", "GET /bookings/client/{id}", "GET", "/bookings/client/{id}"),
            ("BOOK-6", "PUT /bookings/client/{id}", "PUT", "/bookings/client/{id}"),
            ("BOOK-7", "PUT /bookings/waiter/{id}", "PUT", "/bookings/waiter/{id}"),
        ]:
            skip(
                ctx,
                step=step,
                name=name,
                method=method,
                path=path,
                reason="no free slots discovered in BOOK-1",
            )
        return

    execute(
        ctx,
        step="BOOK-2",
        name="GET /bookings/waiter/tables — waiter availability window",
        method="GET",
        path="/bookings/waiter/tables",
        token=token_max,
        auth_user=WAITER_EMAIL,
        params={
            "location_id": airport_id,
            "date": booking_date,
            "guests_number": 2,
            "from_time": slot_a["start_time"],
            "to_time": slot_a["end_time"],
        },
        expected=(200,),
    )

    def _capture_reservation(resp):
        """Store the created reservation id for all downstream suites."""
        res_id = resp.json().get("reservationId") or resp.json().get("id")
        if not res_id:
            return False, "response missing reservationId"
        ctx.state["res_id_a"] = res_id
        return True, ""

    def _create_db_check(resp):
        """Verify the reservations table now holds the new row as Reserved."""
        res_id = resp.json().get("reservationId") or resp.json().get("id")
        appeared = wait_until(lambda: get_by_id(reservations_tbl, res_id) is not None)
        row = get_by_id(reservations_tbl, res_id)
        status_ok = bool(row) and row.get("status") == "Reserved"
        guests_ok = bool(row) and row.get("number_of_guests") == 2
        return [
            make_check(
                "reservations",
                "row created with status='Reserved' and number_of_guests=2",
                appeared and status_ok and guests_ok,
                before="(no row)",
                after=row_summary(row, ["status", "number_of_guests", "date"]),
            )
        ]

    execute(
        ctx,
        step="BOOK-3",
        name="POST /bookings/client — kate books Airport table 1 (slot A)",
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
        response_check=_capture_reservation,
        db_check=_create_db_check,
    )

    res_id = ctx.state.get("res_id_a")
    if not res_id:
        for step, name, method, path in [
            ("BOOK-4", "GET /bookings/client", "GET", "/bookings/client"),
            ("BOOK-5", "GET /bookings/client/{id}", "GET", "/bookings/client/{id}"),
            ("BOOK-6", "PUT /bookings/client/{id}", "PUT", "/bookings/client/{id}"),
            ("BOOK-7", "PUT /bookings/waiter/{id}", "PUT", "/bookings/waiter/{id}"),
        ]:
            skip(
                ctx,
                step=step,
                name=name,
                method=method,
                path=path,
                reason="no reservation created in BOOK-3",
            )
        return

    execute(
        ctx,
        step="BOOK-4",
        name="GET /bookings/client — kate's dashboard lists the booking",
        method="GET",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            any(
                r.get("reservationId") == res_id
                for r in resp.json().get("reservations", [])
            ),
            f"reservation {res_id} not present in dashboard list",
        ),
    )

    execute(
        ctx,
        step="BOOK-5",
        name="GET /bookings/client/{id} — fetch the new reservation",
        method="GET",
        path=f"/bookings/client/{res_id}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("reservationId") == res_id,
            "returned reservationId does not match",
        ),
    )

    before_row = get_by_id(reservations_tbl, res_id)

    def _guests_db_check(_resp):
        """Verify number_of_guests changed from 2 to 3 in DynamoDB."""
        changed = wait_until(
            lambda: (
                (get_by_id(reservations_tbl, res_id) or {}).get("number_of_guests") == 3
            )
        )
        after_row = get_by_id(reservations_tbl, res_id)
        return [
            make_check(
                "reservations",
                "number_of_guests updated 2 -> 3",
                changed,
                before=row_summary(before_row, ["status", "number_of_guests"]),
                after=row_summary(after_row, ["status", "number_of_guests"]),
            )
        ]

    execute(
        ctx,
        step="BOOK-6",
        name="PUT /bookings/client/{id} — kate raises guests to 3",
        method="PUT",
        path=f"/bookings/client/{res_id}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={"guestsNumber": 3},
        expected=(200,),
        db_check=_guests_db_check,
    )

    def _status_db_check(_resp):
        """Verify status moved to 'In Progress' in DynamoDB."""
        changed = wait_until(
            lambda: (
                (get_by_id(reservations_tbl, res_id) or {}).get("status")
                == "In Progress"
            )
        )
        after_row = get_by_id(reservations_tbl, res_id)
        return [
            make_check(
                "reservations",
                "status updated 'Reserved' -> 'In Progress'",
                changed,
                before="status='Reserved'",
                after=row_summary(after_row, ["status", "number_of_guests"]),
            )
        ]

    execute(
        ctx,
        step="BOOK-7",
        name="PUT /bookings/waiter/{id} — max starts the reservation",
        method="PUT",
        path=f"/bookings/waiter/{res_id}",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={"status": "In Progress"},
        expected=(200,),
        db_check=_status_db_check,
    )

    execute(
        ctx,
        step="BOOK-8",
        name="POST /bookings/client — waiter without existingCustomer flag is rejected",
        method="POST",
        path="/bookings/client",
        token=token_max,
        auth_user=WAITER_EMAIL,
        body={
            "locationId": airport_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_b["start_time"],
            "timeTo": slot_b["end_time"],
        },
        expected=(422,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="BOOK-9",
        name="GET /bookings/tables — missing guests_number is rejected",
        method="GET",
        path="/bookings/tables",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        params={"location_id": airport_id, "date": booking_date},
        expected=(422,),
    )

    execute(
        ctx,
        step="BOOK-10",
        name="GET /bookings/tables — non-integer guests_number is rejected",
        method="GET",
        path="/bookings/tables",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        params={
            "location_id": airport_id,
            "date": booking_date,
            "guests_number": "two",
        },
        expected=(422,),
    )

    base_booking = {
        "locationId": airport_id,
        "tableNumber": 1,
        "date": booking_date,
        "guestsNumber": 2,
        "timeFrom": slot_b["start_time"],
        "timeTo": slot_b["end_time"],
    }

    execute(
        ctx,
        step="BOOK-11",
        name="POST /bookings/client — missing tableNumber is rejected",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={k: v for k, v in base_booking.items() if k != "tableNumber"},
        expected=(422,),
    )

    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    execute(
        ctx,
        step="BOOK-12",
        name="POST /bookings/client — booking in the past is rejected",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={**base_booking, "date": yesterday},
        expected=(422,),
    )

    far_future = (datetime.now(UTC).date() + timedelta(days=45)).isoformat()
    execute(
        ctx,
        step="BOOK-13",
        name="POST /bookings/client — booking >30 days ahead is rejected",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={**base_booking, "date": far_future},
        expected=(422,),
    )

    execute(
        ctx,
        step="BOOK-14",
        name="POST /bookings/client — guestsNumber above limit (11) is rejected",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={**base_booking, "guestsNumber": 11},
        expected=(422,),
    )

    execute(
        ctx,
        step="BOOK-15",
        name="POST /bookings/client — timeTo before timeFrom is rejected",
        method="POST",
        path="/bookings/client",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            **base_booking,
            "timeFrom": slot_b["end_time"],
            "timeTo": slot_b["start_time"],
        },
        expected=(422,),
    )

    token_alice = ctx.token("alice@example.com")

    def _no_double_booking_db_check(_resp):
        """Verify the conflicting attempt did not create another reservation."""
        row = get_by_id(reservations_tbl, res_id)
        return [
            make_check(
                "reservations",
                "slot A still belongs to kate's reservation only",
                bool(row) and row.get("status") == "In Progress",
                before=f"reservation {res_id} holds slot A",
                after=row_summary(row, ["status", "number_of_guests"]),
            )
        ]

    execute(
        ctx,
        step="BOOK-16",
        name="POST /bookings/client — double-booking an occupied slot returns 409",
        method="POST",
        path="/bookings/client",
        token=token_alice,
        auth_user="alice@example.com",
        body={
            "locationId": airport_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_a["start_time"],
            "timeTo": slot_a["end_time"],
        },
        expected=(409,),
        db_check=_no_double_booking_db_check,
    )

    execute(
        ctx,
        step="BOOK-17",
        name="POST /bookings/client — missing token is rejected",
        method="POST",
        path="/bookings/client",
        body=base_booking,
        expected=(401,),
    )

    execute(
        ctx,
        step="BOOK-18",
        name="PUT /bookings/client/{id} — empty update payload is rejected",
        method="PUT",
        path=f"/bookings/client/{res_id}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={},
        expected=(422,),
    )

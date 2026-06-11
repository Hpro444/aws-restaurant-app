"""E2E suite for the /feedbacks route group (context, create, update, guards)."""

from __future__ import annotations

import uuid
from uuid import NAMESPACE_URL, uuid5

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import make_check, scan_eq, wait_until
from e2e.http_client import execute, skip


def run(ctx) -> None:
    """Exercise feedback context, creation for both types, edit, and guards."""
    res_id = ctx.state.get("res_id_a")
    if not res_id:
        skip(
            ctx,
            step="FB-1",
            name="feedback flow",
            method="POST",
            path="/feedbacks",
            reason="no finished reservation available from earlier suites",
        )
        return

    token_kate = ctx.token(CUSTOMER_EMAIL)
    max_waiter_id = ctx.ids["waiters"][WAITER_EMAIL]
    cuisine_tbl = ctx.table("feedback_cuisine")
    service_tbl = ctx.table("feedback_service")

    execute(
        ctx,
        step="FB-1",
        name="GET /feedbacks/context/{id} — modal context for the reservation",
        method="GET",
        path=f"/feedbacks/context/{res_id}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("waiter_id") == max_waiter_id,
            f"expected waiter_id {max_waiter_id}, got {resp.json().get('waiter_id')}",
        ),
    )

    def _culinary_db_check(_resp):
        """Verify a feedback_cuisine row with rate=5 exists for the reservation."""
        appeared = wait_until(
            lambda: any(
                r.get("rate") == 5 for r in scan_eq(cuisine_tbl, reservation_id=res_id)
            )
        )
        rows = scan_eq(cuisine_tbl, reservation_id=res_id)
        return [
            make_check(
                "feedback_cuisine",
                "row created with rate=5 for the reservation",
                appeared,
                before="0 rows for this reservation",
                after=f"{len(rows)} row(s), rate={[r.get('rate') for r in rows]}",
            )
        ]

    execute(
        ctx,
        step="FB-2",
        name="POST /feedbacks — kate leaves culinary feedback (rating 5)",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "type": "culinary",
            "rating": 5,
            "comment": "Excellent flavors, beautifully presented.",
        },
        expected=(201,),
        db_check=_culinary_db_check,
    )

    def _service_db_check(_resp):
        """Verify a feedback_service row with rate=4 exists for the reservation."""
        appeared = wait_until(
            lambda: any(
                r.get("rate") == 4 for r in scan_eq(service_tbl, reservation_id=res_id)
            )
        )
        rows = scan_eq(service_tbl, reservation_id=res_id)
        return [
            make_check(
                "feedback_service",
                "row created with rate=4 for the reservation",
                appeared,
                before="0 rows for this reservation",
                after=f"{len(rows)} row(s), rate={[r.get('rate') for r in rows]}",
            )
        ]

    execute(
        ctx,
        step="FB-3",
        name="POST /feedbacks — kate leaves service feedback (rating 4)",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "type": "service",
            "rating": 4,
            "comment": "Attentive and professional service.",
        },
        expected=(201,),
        db_check=_service_db_check,
    )

    def _edit_db_check(_resp):
        """Verify the culinary feedback rate changed from 5 to 3."""
        changed = wait_until(
            lambda: any(
                r.get("rate") == 3 for r in scan_eq(cuisine_tbl, reservation_id=res_id)
            )
        )
        rows = scan_eq(cuisine_tbl, reservation_id=res_id)
        return [
            make_check(
                "feedback_cuisine",
                "rate updated 5 -> 3, row count unchanged",
                changed and len(rows) == 1,
                before="1 row, rate=5",
                after=f"{len(rows)} row(s), rate={[r.get('rate') for r in rows]}",
            )
        ]

    execute(
        ctx,
        step="FB-4",
        name="PUT /feedbacks — kate edits culinary feedback (5 -> 3)",
        method="PUT",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "type": "culinary",
            "rating": 3,
            "comment": "Good, but the dessert was underwhelming.",
        },
        expected=(200,),
        db_check=_edit_db_check,
    )

    def _duplicate_db_check(_resp):
        """Verify the duplicate did not add a second cuisine row."""
        rows = scan_eq(cuisine_tbl, reservation_id=res_id)
        return [
            make_check(
                "feedback_cuisine",
                "duplicate rejected; row count still 1",
                len(rows) == 1,
                before="1 row",
                after=f"{len(rows)} row(s)",
            )
        ]

    execute(
        ctx,
        step="FB-5",
        name="POST /feedbacks — duplicate culinary feedback is rejected",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": res_id,
            "type": "culinary",
            "rating": 2,
            "comment": "Second culinary attempt.",
        },
        expected=(409,),
        db_check=_duplicate_db_check,
    )

    execute(
        ctx,
        step="FB-6",
        name="POST /feedbacks — waiter role is forbidden",
        method="POST",
        path="/feedbacks",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        body={
            "reservation_id": res_id,
            "type": "service",
            "rating": 5,
            "comment": "Waiter trying to self-review.",
        },
        expected=(403,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="FB-7",
        name="POST /feedbacks — rating 0 (below range) is rejected",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={"reservation_id": res_id, "type": "service", "rating": 0},
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-8",
        name="POST /feedbacks — rating 6 (above range) is rejected",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={"reservation_id": res_id, "type": "service", "rating": 6},
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-9",
        name="POST /feedbacks — invalid type is rejected",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={"reservation_id": res_id, "type": "ambience", "rating": 4},
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-10",
        name="POST /feedbacks — missing reservation_id is rejected",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={"type": "culinary", "rating": 4},
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-11",
        name="POST /feedbacks — unknown reservation returns 404",
        method="POST",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": str(uuid.uuid4()),
            "type": "culinary",
            "rating": 4,
        },
        expected=(404,),
    )

    alice_reservation = (
        ctx.ids.get("reservations", {}).get("alice@example.com") or {}
    ).get("id")
    if alice_reservation:
        execute(
            ctx,
            step="FB-12",
            name="POST /feedbacks — another customer's reservation is forbidden",
            method="POST",
            path="/feedbacks",
            token=token_kate,
            auth_user=CUSTOMER_EMAIL,
            body={
                "reservation_id": alice_reservation,
                "type": "culinary",
                "rating": 1,
            },
            expected=(403,),
        )
    else:
        skip(
            ctx,
            step="FB-12",
            name="POST /feedbacks — another customer's reservation is forbidden",
            method="POST",
            path="/feedbacks",
            reason="no seeded reservation for alice@example.com in ids.json",
        )

    execute(
        ctx,
        step="FB-13",
        name="PUT /feedbacks — unknown reservation returns 404",
        method="PUT",
        path="/feedbacks",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "reservation_id": str(uuid.uuid4()),
            "type": "culinary",
            "rating": 4,
        },
        expected=(404,),
    )

    execute(
        ctx,
        step="FB-14",
        name="GET /feedbacks/context/{id} — waiter role is forbidden",
        method="GET",
        path=f"/feedbacks/context/{res_id}",
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        expected=(403,),
    )

    # ── GET /feedback/{feedback_id} — single-feedback retrieval ──────────────

    culinary_feedback_id = str(uuid5(NAMESPACE_URL, f"culinary:{res_id}"))
    service_feedback_id = str(uuid5(NAMESPACE_URL, f"service:{res_id}"))

    execute(
        ctx,
        step="FB-15",
        name="GET /feedback/{id}?type=cuisine — kate retrieves her culinary feedback",
        method="GET",
        path=f"/feedback/{culinary_feedback_id}",
        params={"type": "cuisine"},
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("rate") == 3,
            f"expected rate=3 (after edit), got {resp.json().get('rate')}",
        ),
    )

    execute(
        ctx,
        step="FB-16",
        name="GET /feedback/{id}?type=service — kate retrieves her service feedback",
        method="GET",
        path=f"/feedback/{service_feedback_id}",
        params={"type": "service"},
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("rate") == 4,
            f"expected rate=4, got {resp.json().get('rate')}",
        ),
    )

    execute(
        ctx,
        step="FB-17",
        name="GET /feedback/{id} — missing type param is rejected",
        method="GET",
        path=f"/feedback/{culinary_feedback_id}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-18",
        name="GET /feedback/{id}?type=ambience — invalid type is rejected",
        method="GET",
        path=f"/feedback/{culinary_feedback_id}",
        params={"type": "ambience"},
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-19",
        name="GET /feedback/not-a-uuid?type=cuisine — non-UUID feedback_id is rejected",
        method="GET",
        path="/feedback/not-a-valid-uuid",
        params={"type": "cuisine"},
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(422,),
    )

    execute(
        ctx,
        step="FB-20",
        name="GET /feedback/{id}?type=cuisine — waiter role is forbidden",
        method="GET",
        path=f"/feedback/{culinary_feedback_id}",
        params={"type": "cuisine"},
        token=ctx.token(WAITER_EMAIL),
        auth_user=WAITER_EMAIL,
        expected=(403,),
    )

    execute(
        ctx,
        step="FB-21",
        name="GET /feedback/{id}?type=cuisine — unknown feedback_id returns empty list",
        method="GET",
        path=f"/feedback/{uuid.uuid4()}",
        params={"type": "cuisine"},
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            resp.json() == [],
            f"expected empty list [], got {resp.json()!r}",
        ),
    )

    token_alice = ctx.token("alice@example.com")
    if token_alice:
        execute(
            ctx,
            step="FB-22",
            name="GET /feedback/{id}?type=cuisine — alice cannot access kate's feedback",
            method="GET",
            path=f"/feedback/{culinary_feedback_id}",
            params={"type": "cuisine"},
            token=token_alice,
            auth_user="alice@example.com",
            expected=(403,),
        )
    else:
        skip(
            ctx,
            step="FB-22",
            name="GET /feedback/{id}?type=cuisine — alice cannot access kate's feedback",
            method="GET",
            path=f"/feedback/{culinary_feedback_id}",
            reason="no token for alice@example.com in tokens.json",
        )

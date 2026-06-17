"""E2E suite for the /locations route group."""

from __future__ import annotations

import uuid

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import count_items, make_check, scan_eq
from e2e.http_client import execute


def run(ctx) -> None:
    """Exercise every locations endpoint, cross-checking counts against DynamoDB."""
    airport_id = ctx.ids["locations"]["airport"]
    token_kate = ctx.token(CUSTOMER_EMAIL)
    token_max = ctx.token(WAITER_EMAIL)

    def _locations_db_check(resp):
        """Compare the returned location count against the locations table."""
        api_count = len(resp.json())
        db_count = count_items(ctx.table("locations"))
        return [
            make_check(
                "locations",
                "API location count equals table item count (read-only, no change)",
                api_count == db_count,
                before=f"table rows: {db_count}",
                after=f"API returned: {api_count}",
            )
        ]

    execute(
        ctx,
        step="LOC-1",
        name="GET /locations — list all restaurant locations",
        method="GET",
        path="/locations",
        expected=(200,),
        db_check=_locations_db_check,
    )

    execute(
        ctx,
        step="LOC-2",
        name="GET /locations/select-options — address picker options",
        method="GET",
        path="/locations/select-options",
        expected=(200,),
        response_check=lambda resp: (
            len(resp.json()) == 3,
            f"expected 3 options, got {len(resp.json())}",
        ),
    )

    execute(
        ctx,
        step="LOC-3",
        name="GET /locations/{id} — fetch the Airport location",
        method="GET",
        path=f"/locations/{airport_id}",
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("id") == airport_id,
            "returned id does not match requested id",
        ),
    )

    execute(
        ctx,
        step="LOC-4",
        name="GET /locations/{id}/speciality-dishes — Airport specialities",
        method="GET",
        path=f"/locations/{airport_id}/speciality-dishes",
        expected=(200,),
        response_check=lambda resp: (
            isinstance(resp.json(), list),
            "expected a JSON array",
        ),
    )

    execute(
        ctx,
        step="LOC-5",
        name="GET /locations/{id}/valid-slot-times — Airport slot grid",
        method="GET",
        path=f"/locations/{airport_id}/valid-slot-times",
        expected=(200,),
        response_check=lambda resp: (
            isinstance(resp.json(), dict) and bool(resp.json()),
            "expected a non-empty JSON object of slot times",
        ),
    )

    def _feedbacks_db_check(resp):
        """Compare totalElements with the cuisine feedback rows for Airport."""
        total = resp.json().get("totalElements")
        rows = scan_eq(ctx.table("feedback_cuisine"), location_id=airport_id)
        return [
            make_check(
                "feedback_cuisine",
                "totalElements equals cuisine feedback rows for Airport (read-only)",
                total == len(rows),
                before=f"table rows for location: {len(rows)}",
                after=f"API totalElements: {total}",
            )
        ]

    execute(
        ctx,
        step="LOC-6",
        name="GET /locations/{id}/feedbacks?type=cuisine — paged feedback",
        method="GET",
        path=f"/locations/{airport_id}/feedbacks",
        params={"type": "cuisine", "page": 0, "size": 20},
        expected=(200,),
        db_check=_feedbacks_db_check,
    )

    def _tables_db_check(resp):
        """Compare returned table count against the tables table for Airport."""
        api_count = len(resp.json())
        rows = scan_eq(ctx.table("tables"), location_id=airport_id)
        return [
            make_check(
                "tables",
                "API table count equals Airport rows in tables table (read-only)",
                api_count == len(rows),
                before=f"table rows for location: {len(rows)}",
                after=f"API returned: {api_count}",
            )
        ]

    execute(
        ctx,
        step="LOC-7",
        name="GET /locations/{id}/tables — waiter-only table list",
        method="GET",
        path=f"/locations/{airport_id}/tables",
        token=token_max,
        auth_user=WAITER_EMAIL,
        expected=(200,),
        db_check=_tables_db_check,
    )

    execute(
        ctx,
        step="LOC-8",
        name="GET /locations/{id} — malformed UUID is rejected",
        method="GET",
        path="/locations/not-a-uuid",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(422,),
    )

    execute(
        ctx,
        step="LOC-9",
        name="GET /locations/{id} — unknown UUID returns 404",
        method="GET",
        path=f"/locations/{uuid.uuid4()}",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(404,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="LOC-10",
        name="GET /locations/{id}/feedbacks — missing type is rejected",
        method="GET",
        path=f"/locations/{airport_id}/feedbacks",
        expected=(422,),
    )

    execute(
        ctx,
        step="LOC-11",
        name="GET /locations/{id}/feedbacks — invalid type is rejected",
        method="GET",
        path=f"/locations/{airport_id}/feedbacks",
        params={"type": "ambience"},
        expected=(422,),
    )

    execute(
        ctx,
        step="LOC-12",
        name="GET /locations/{id}/feedbacks — invalid sort is rejected",
        method="GET",
        path=f"/locations/{airport_id}/feedbacks",
        params={"type": "cuisine", "sort": "price,up"},
        expected=(422,),
    )

    execute(
        ctx,
        step="LOC-13",
        name="GET /locations/{id}/feedbacks — page beyond range is rejected",
        method="GET",
        path=f"/locations/{airport_id}/feedbacks",
        params={"type": "cuisine", "page": 999, "size": 20},
        expected=(422,),
    )

    execute(
        ctx,
        step="LOC-14",
        name="GET /locations/{id}/tables — customer role is forbidden",
        method="GET",
        path=f"/locations/{airport_id}/tables",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(403,),
    )

    execute(
        ctx,
        step="LOC-15",
        name="GET /locations/{id}/tables — missing token is rejected",
        method="GET",
        path=f"/locations/{airport_id}/tables",
        expected=(401,),
    )

"""E2E suite for the /dishes route group."""

from __future__ import annotations

import uuid

from e2e.http_client import execute


def run(ctx) -> None:
    """Exercise the public dish endpoints, including 404 and 422 paths."""
    wrap_dish_id = ctx.ids["dishes"]["airport"]["Grilled Chicken Wrap"]

    execute(
        ctx,
        step="DISH-1",
        name="GET /dishes — list all dishes",
        method="GET",
        path="/dishes",
        expected=(200,),
        response_check=lambda resp: (
            isinstance(resp.json(), list) and len(resp.json()) > 0,
            "expected a non-empty dish list",
        ),
    )

    execute(
        ctx,
        step="DISH-2",
        name="GET /dishes/popular — popular dishes across locations",
        method="GET",
        path="/dishes/popular",
        expected=(200,),
        response_check=lambda resp: (
            isinstance(resp.json(), list),
            "expected a JSON array",
        ),
    )

    execute(
        ctx,
        step="DISH-3",
        name="GET /dishes?sort=price,asc — sorted dish list",
        method="GET",
        path="/dishes",
        params={"sort": "price,asc"},
        expected=(200,),
        response_check=lambda resp: (
            [d.get("price") for d in resp.json()]
            == sorted(d.get("price") for d in resp.json()),
            "dish list is not sorted by ascending price",
        ),
    )

    execute(
        ctx,
        step="DISH-4",
        name="GET /dishes/{id} — fetch the Grilled Chicken Wrap",
        method="GET",
        path=f"/dishes/{wrap_dish_id}",
        expected=(200,),
        response_check=lambda resp: (
            resp.json().get("id") == wrap_dish_id,
            "returned id does not match requested id",
        ),
    )

    execute(
        ctx,
        step="DISH-5",
        name="GET /dishes/{id} — unknown UUID returns 404",
        method="GET",
        path=f"/dishes/{uuid.uuid4()}",
        expected=(404,),
    )

    execute(
        ctx,
        step="DISH-6",
        name="GET /dishes?sort=bogus — invalid sort is rejected",
        method="GET",
        path="/dishes",
        params={"sort": "bogus"},
        expected=(422,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="DISH-7",
        name="GET /dishes?dishType=bogus — invalid dish type is rejected",
        method="GET",
        path="/dishes",
        params={"dishType": "bogus"},
        expected=(422,),
    )

    execute(
        ctx,
        step="DISH-8",
        name="GET /dishes/{id} — malformed UUID is rejected",
        method="GET",
        path="/dishes/not-a-uuid",
        expected=(422,),
    )

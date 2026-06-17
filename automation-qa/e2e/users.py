"""E2E suite for the /users route group (profile and waiter location)."""

from __future__ import annotations

from e2e.config import CUSTOMER_EMAIL, WAITER_EMAIL
from e2e.db import get_by_id, make_check, row_summary, wait_until
from e2e.http_client import execute


def run(ctx) -> None:
    """Exercise profile read/update and the waiter location endpoint."""
    token_kate = ctx.token(CUSTOMER_EMAIL)
    token_max = ctx.token(WAITER_EMAIL)
    kate_id = ctx.ids["customers"][CUSTOMER_EMAIL]
    airport_id = ctx.ids["locations"]["airport"]
    customers_tbl = ctx.table("customers")

    original: dict = {}

    def _capture_profile(resp):
        """Remember kate's current profile so the update can be reverted."""
        data = resp.json()
        original.update(data)
        return data.get("email") == CUSTOMER_EMAIL, (
            f"profile email {data.get('email')!r} != {CUSTOMER_EMAIL!r}"
        )

    execute(
        ctx,
        step="USER-1",
        name="GET /users/profile — kate reads her own profile",
        method="GET",
        path="/users/profile",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        expected=(200,),
        response_check=_capture_profile,
    )

    before_row = get_by_id(customers_tbl, kate_id)
    new_first_name = "Kate-E2E"

    def _profile_update_db_check(_resp):
        """Verify the customers row reflects the new first name."""
        changed = wait_until(
            lambda: (
                (get_by_id(customers_tbl, kate_id) or {}).get("fname") == new_first_name
            )
        )
        after_row = get_by_id(customers_tbl, kate_id)
        return [
            make_check(
                "customers",
                f"fname updated to {new_first_name!r}",
                changed,
                before=row_summary(before_row, ["fname", "lname"]),
                after=row_summary(after_row, ["fname", "lname"]),
            )
        ]

    update_body = {
        "first_name": new_first_name,
        "last_name": original.get("last_name", "Customer"),
        "image_url": original.get("image_url") or "https://example.com/avatar.png",
    }
    execute(
        ctx,
        step="USER-2",
        name="PUT /users/profile — kate changes her first name",
        method="PUT",
        path="/users/profile",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body=update_body,
        expected=(200,),
        db_check=_profile_update_db_check,
    )

    restored_first_name = original.get("first_name", "Kate")

    def _profile_restore_db_check(_resp):
        """Verify the customers row was restored to the original first name."""
        restored = wait_until(
            lambda: (
                (get_by_id(customers_tbl, kate_id) or {}).get("fname")
                == restored_first_name
            )
        )
        after_row = get_by_id(customers_tbl, kate_id)
        return [
            make_check(
                "customers",
                f"fname restored to {restored_first_name!r}",
                restored,
                before=f"fname={new_first_name!r}",
                after=row_summary(after_row, ["fname", "lname"]),
            )
        ]

    execute(
        ctx,
        step="USER-3",
        name="PUT /users/profile — kate restores her original name",
        method="PUT",
        path="/users/profile",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "first_name": restored_first_name,
            "last_name": original.get("last_name", "Customer"),
            "image_url": original.get("image_url") or "https://example.com/avatar.png",
        },
        expected=(200,),
        db_check=_profile_restore_db_check,
    )

    execute(
        ctx,
        step="USER-4",
        name="GET /users/waiter/location — max's assigned location",
        method="GET",
        path="/users/waiter/location",
        token=token_max,
        auth_user=WAITER_EMAIL,
        expected=(200,),
        response_check=lambda resp: (
            airport_id in str(resp.json()),
            f"expected Airport location id {airport_id} in response",
        ),
    )

    execute(
        ctx,
        step="USER-5",
        name="GET /users/profile — missing token is rejected",
        method="GET",
        path="/users/profile",
        expected=(401,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="USER-6",
        name="PUT /users/profile — missing last_name is rejected",
        method="PUT",
        path="/users/profile",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "first_name": "Kate",
            "image_url": "https://example.com/avatar.png",
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="USER-7",
        name="PUT /users/profile — non-http image_url is rejected",
        method="PUT",
        path="/users/profile",
        token=token_kate,
        auth_user=CUSTOMER_EMAIL,
        body={
            "first_name": "Kate",
            "last_name": "Customer",
            "image_url": "ftp://example.com/avatar.png",
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="USER-8",
        name="GET /users/profile — garbage bearer token is rejected",
        method="GET",
        path="/users/profile",
        token="not-a-real-token",
        expected=(401,),
    )

"""E2E suite for the /auth route group (sign-up, sign-in, refresh, logout)."""

from __future__ import annotations

import time

from e2e.config import SEED_PASSWORD
from e2e.db import make_check, scan_eq, wait_until
from e2e.http_client import execute


def run(ctx) -> None:
    """Exercise registration and the full token lifecycle for a fresh user."""
    email = f"e2e.user.{int(time.time())}@example.com"
    ctx.state["new_user_email"] = email
    customers_tbl = ctx.table("customers")

    def _signup_db_check(_resp):
        """Verify a customer row was created for the registered email."""
        found = wait_until(lambda: len(scan_eq(customers_tbl, email=email)) == 1)
        rows = scan_eq(customers_tbl, email=email)
        return [
            make_check(
                "customers",
                f"row created for {email}",
                found,
                before="0 rows with this email",
                after=f"{len(rows)} row(s)"
                + (f", id={rows[0].get('id')}" if rows else ""),
            )
        ]

    execute(
        ctx,
        step="AUTH-1",
        name="POST /auth/sign-up — register a brand-new customer",
        method="POST",
        path="/auth/sign-up",
        body={
            "firstName": "E2E",
            "lastName": "Tester",
            "email": email,
            "password": SEED_PASSWORD,
        },
        expected=(201,),
        db_check=_signup_db_check,
    )

    def _capture_tokens(resp):
        """Stash the new user's tokens for the refresh/logout steps."""
        data = resp.json()
        access = data.get("access_token") or data.get("accessToken")
        refresh = data.get("refresh_token") or data.get("refreshToken")
        if not access or not refresh:
            return False, "response missing access_token/refresh_token"
        ctx.state["new_user_access"] = access
        ctx.state["new_user_refresh"] = refresh
        return True, ""

    execute(
        ctx,
        step="AUTH-2",
        name="POST /auth/sign-in — sign in as the new customer",
        method="POST",
        path="/auth/sign-in",
        body={"email": email, "password": SEED_PASSWORD},
        expected=(200,),
        response_check=_capture_tokens,
    )

    execute(
        ctx,
        step="AUTH-3",
        name="POST /auth/sign-in — wrong password is rejected",
        method="POST",
        path="/auth/sign-in",
        body={"email": email, "password": "WrongPass123@"},
        expected=(401,),
    )

    refresh_token = ctx.state.get("new_user_refresh", "")
    execute(
        ctx,
        step="AUTH-4",
        name="POST /auth/refresh — exchange refresh token for new access token",
        method="POST",
        path="/auth/refresh",
        body={"refresh_token": refresh_token},
        expected=(200,),
        response_check=lambda resp: (
            bool(resp.json().get("access_token")),
            "response missing access_token",
        ),
    )

    execute(
        ctx,
        step="AUTH-5",
        name="POST /auth/logout — revoke the refresh token",
        method="POST",
        path="/auth/logout",
        body={"refresh_token": refresh_token},
        expected=(200,),
    )

    # ── Edge cases: validation and error handling ──────────────────────────
    execute(
        ctx,
        step="AUTH-6",
        name="POST /auth/sign-up — missing password is rejected",
        method="POST",
        path="/auth/sign-up",
        body={"firstName": "E2E", "lastName": "Tester", "email": email},
        expected=(422,),
    )

    execute(
        ctx,
        step="AUTH-7",
        name="POST /auth/sign-up — malformed email is rejected",
        method="POST",
        path="/auth/sign-up",
        body={
            "firstName": "E2E",
            "lastName": "Tester",
            "email": "not-an-email",
            "password": SEED_PASSWORD,
        },
        expected=(422,),
    )

    execute(
        ctx,
        step="AUTH-8",
        name="POST /auth/sign-up — weak password is rejected",
        method="POST",
        path="/auth/sign-up",
        body={
            "firstName": "E2E",
            "lastName": "Tester",
            "email": f"e2e.weak.{int(time.time())}@example.com",
            "password": "weak",
        },
        expected=(422,),
    )

    def _no_new_customer_db_check(_resp):
        """Verify the duplicate registration did not add a second customer row."""
        rows = scan_eq(customers_tbl, email=email)
        return [
            make_check(
                "customers",
                "duplicate sign-up rejected; still exactly 1 row for the email",
                len(rows) == 1,
                before="1 row",
                after=f"{len(rows)} row(s)",
            )
        ]

    execute(
        ctx,
        step="AUTH-9",
        name="POST /auth/sign-up — duplicate email returns 409",
        method="POST",
        path="/auth/sign-up",
        body={
            "firstName": "E2E",
            "lastName": "Tester",
            "email": email,
            "password": SEED_PASSWORD,
        },
        expected=(409,),
        db_check=_no_new_customer_db_check,
    )

    execute(
        ctx,
        step="AUTH-10",
        name="POST /auth/sign-in — missing password is rejected",
        method="POST",
        path="/auth/sign-in",
        body={"email": email},
        expected=(422,),
    )

    execute(
        ctx,
        step="AUTH-11",
        name="POST /auth/refresh — missing refresh_token is rejected",
        method="POST",
        path="/auth/refresh",
        body={},
        expected=(422,),
    )

    execute(
        ctx,
        step="AUTH-12",
        name="POST /auth/logout — missing refresh_token is rejected",
        method="POST",
        path="/auth/logout",
        body={},
        expected=(422,),
    )

    execute(
        ctx,
        step="AUTH-13",
        name="POST /auth/sign-in — malformed JSON body is rejected",
        method="POST",
        path="/auth/sign-in",
        raw_body='{"email": "broken json...',
        expected=(422,),
    )

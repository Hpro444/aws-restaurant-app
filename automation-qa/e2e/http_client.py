"""HTTP step executor: sends requests, prints diffs, and records results."""

from __future__ import annotations

import json
import time

import requests

from e2e.recorder import StepResult

_GREEN = "\033[92m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

SEP = "─" * 70

_MAX_BODY_CHARS = 4000


_SENSITIVE_KEY_PARTS = ("password", "token")


def _redact(payload: dict | None) -> dict | None:
    """Return a copy of a request body with credential-bearing values masked."""
    if payload is None:
        return None
    return {
        key: (
            "***"
            if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)
            else value
        )
        for key, value in payload.items()
    }


def _redact_deep(value):
    """Recursively mask credential-bearing values inside a JSON structure."""
    if isinstance(value, dict):
        return {
            key: (
                "***"
                if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)
                else _redact_deep(val)
            )
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact_deep(item) for item in value]
    return value


def _pretty_body(resp: requests.Response) -> str:
    """Return the response body pretty-printed as JSON with tokens masked."""
    try:
        return json.dumps(_redact_deep(resp.json()), indent=2)
    except Exception:
        return resp.text[:_MAX_BODY_CHARS]


def skip(ctx, *, step: str, name: str, method: str, path: str, reason: str) -> None:
    """Record a step as failed-skipped when its prerequisites are missing.

    No HTTP request is sent — the record exists so the report shows the step
    was not executed and why.
    """
    print(
        f"\n{SEP}\n  {_BOLD}{step}{_RESET} | {name}\n  {_RED}⊘ SKIPPED{_RESET}: {reason}\n{SEP}"
    )
    ctx.recorder.add(
        StepResult(
            step=step,
            name=name,
            method=method,
            path=path,
            auth_user="-",
            expected="-",
            status_code=None,
            response_body="(step skipped — no request was sent)",
            http_passed=False,
            reason=f"skipped: {reason}",
        )
    )


def execute(
    ctx,
    *,
    step: str,
    name: str,
    method: str,
    path: str,
    token: str = "",
    auth_user: str = "anonymous",
    body: dict | None = None,
    params: dict | None = None,
    raw_body: str | None = None,
    expected: tuple[int, ...] = (200,),
    response_check=None,
    db_check=None,
) -> requests.Response | None:
    """Send one API request, assert it, run DB verification, and record it all.

    Args:
        ctx: The shared E2EContext.
        step: Short step id shown in the summary (e.g. ``BOOK-3``).
        name: Human-readable description of the step.
        method: HTTP method.
        path: Route path appended to the base URL.
        token: Bearer access token; empty sends no Authorization header.
        auth_user: Label of the acting user for the report.
        body: Optional JSON request body.
        params: Optional query-string parameters.
        raw_body: Optional raw (possibly malformed) body string sent verbatim
            instead of ``body`` — used to test JSON parsing error handling.
        expected: HTTP status codes treated as a pass.
        response_check: Optional ``fn(resp) -> tuple[bool, str]`` for extra
            response content assertions; only invoked when the status matches.
        db_check: Optional ``fn(resp) -> list[DbCheck]`` performing DynamoDB
            verification after the call; only invoked when the status matches.

    Returns:
        The requests Response, or None when the request itself errored.

    """
    print(f"\n{SEP}")
    print(f"  {_BOLD}{step}{_RESET} | {name}")
    print(f"  Expected : HTTP {'/'.join(str(c) for c in expected)}")
    print(SEP)

    url = ctx.base_url + "/" + path.lstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if raw_body is not None:
        body = {"_raw_body": raw_body}
        print(f"  Body   : {raw_body!r} (sent verbatim)")
    elif body is not None:
        print(f"  Body   : {json.dumps(body)}")
    if params:
        print(f"  Query  : {params}")

    started = time.monotonic()
    try:
        if raw_body is not None:
            resp = requests.request(
                method,
                url,
                headers=headers,
                data=raw_body.encode("utf-8"),
                params=params,
                timeout=30,
            )
        else:
            resp = requests.request(
                method, url, headers=headers, json=body, params=params, timeout=30
            )
    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        print(f"  {_RED}✗ REQUEST ERROR: {exc}{_RESET}")
        ctx.recorder.add(
            StepResult(
                step=step,
                name=name,
                method=method,
                path=path,
                auth_user=auth_user,
                request_query=params,
                request_body=_redact(body),
                expected="/".join(str(c) for c in expected),
                status_code=None,
                response_body=str(exc)[:_MAX_BODY_CHARS],
                http_passed=False,
                reason=f"request error: {exc}",
                duration_ms=elapsed_ms,
            )
        )
        return None

    elapsed_ms = (time.monotonic() - started) * 1000
    body_text = _pretty_body(resp)

    http_passed = resp.status_code in expected
    reason = "" if http_passed else f"expected {expected}, got {resp.status_code}"

    if http_passed and response_check is not None:
        ok, check_reason = response_check(resp)
        if not ok:
            http_passed = False
            reason = check_reason

    db_checks = []
    if db_check is not None and resp.status_code in expected:
        try:
            db_checks = db_check(resp)
        except Exception as exc:
            from e2e.db import make_check

            db_checks = [
                make_check("?", "db verification raised", False, after=str(exc))
            ]

    color = _GREEN if http_passed else _RED
    print(
        f"  Status : {color}{resp.status_code} {resp.reason}{_RESET}  ({elapsed_ms:.0f} ms)"
    )
    shown = (
        body_text if len(body_text) <= 1200 else body_text[:1200] + "\n  ...(truncated)"
    )
    print(f"  Body   : {shown}")

    for check in db_checks:
        mark = f"{_GREEN}✓{_RESET}" if check.passed else f"{_RED}✗{_RESET}"
        print(f"  DB {mark} [{check.table}] {check.expectation}")
        if check.before:
            print(f"       before: {_DIM}{check.before}{_RESET}")
        if check.after:
            print(f"       after : {_CYAN}{check.after}{_RESET}")

    overall = http_passed and all(c.passed for c in db_checks)
    mark = f"{_GREEN}✓ PASS{_RESET}" if overall else f"{_RED}✗ FAIL{_RESET}"
    note = f"  {_DIM}{reason}{_RESET}" if reason else ""
    print(f"  {mark}  {step}{note}")

    ctx.recorder.add(
        StepResult(
            step=step,
            name=name,
            method=method,
            path=path,
            auth_user=auth_user,
            request_query=params,
            request_body=_redact(body),
            expected="/".join(str(c) for c in expected),
            status_code=resp.status_code,
            response_body=body_text[:_MAX_BODY_CHARS],
            http_passed=http_passed,
            reason=reason,
            db_checks=db_checks,
            duration_ms=elapsed_ms,
        )
    )
    return resp

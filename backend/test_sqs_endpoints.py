"""Automated end-to-end test for SQS triggers and DynamoDB report updates.

Mirrors the test flow and data of the original (interactive) test_endpoints.py
but runs fully automatically: no Enter pauses.  Uses the Airport location and
max@example.com (the waiter assigned to Airport table 1) with kate@example.com
as a clean customer, so every SQS-driven change is visible from a near-zero
baseline and the assigned-waiter authorization check always passes.

For each SQS-triggering step it polls the DynamoDB report tables and prints a
before→after diff, then records a pass/fail assertion.

Usage:
    python test_sqs_endpoints.py

Requires tokens.json and ids.json (produced by quick_seed.py).
AWS credentials are loaded from the syndicate config or the environment.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import boto3
import requests
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError, NoCredentialsError

# ── Paths ─────────────────────────────────────────────────────────────────────

_HERE = pathlib.Path(__file__).parent
_TOKENS_FILE = _HERE / "tokens.json"
_IDS_FILE = _HERE / "ids.json"
_SYNDICATE_CONFIG = (
    _HERE / "restaurant-backend-app" / ".syndicate-config-dev" / "syndicate.yml"
)
_SYNDICATE_ALIASES = (
    _HERE / "restaurant-backend-app" / ".syndicate-config-dev" / "syndicate_aliases.yml"
)

# ── Configuration ─────────────────────────────────────────────────────────────

AWS_REGION = "eu-west-3"
_STAGE = "api"
BASE_URL = ""  # resolved at runtime by _resolve_base_url()

_WAITER_FIELDS = [
    "orders_processed",
    "service_feedback_count",
    "avg_service_feedback",
    "min_service_feedback",
    "orders_processed_delta_pct",
    "avg_service_feedback_delta_pct",
]
_LOCATION_FIELDS = [
    "orders_processed",
    "revenue",
    "cuisine_feedback_count",
    "avg_cuisine_feedback",
    "min_cuisine_feedback",
    "orders_processed_delta_pct",
    "avg_cuisine_feedback_delta_pct",
    "revenue_delta_pct",
]

# ── ANSI colours ──────────────────────────────────────────────────────────────

_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

SEP = "─" * 70
DSEP = "═" * 70


# ── Credential helpers (standalone, no quick_seed import) ─────────────────────


def _extract_yml_value(content: str, key: str) -> str | None:
    """Extract a plain scalar from a YAML key: value line."""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", content, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'") or None


def _load_syndicate_credentials() -> dict | None:
    """Load AWS credentials from syndicate.yml (temp > regular) or return None."""
    if not _SYNDICATE_CONFIG.exists():
        return None
    content = _SYNDICATE_CONFIG.read_text(encoding="utf-8")
    access = _extract_yml_value(content, "temp_aws_access_key_id")
    secret = _extract_yml_value(content, "temp_aws_secret_access_key")
    token = _extract_yml_value(content, "temp_aws_session_token")
    if not (access and secret and token):
        access = _extract_yml_value(content, "aws_access_key_id")
        secret = _extract_yml_value(content, "aws_secret_access_key")
        token = _extract_yml_value(content, "aws_session_token")
    if access and secret and token:
        return {
            "aws_access_key_id": access,
            "aws_secret_access_key": secret,
            "aws_session_token": token,
        }
    return None


def _resolve_base_url(session) -> str | None:
    """Resolve the API Gateway invoke URL from deployed REST APIs.

    Reads resources_prefix and resources_suffix from syndicate.yml, then finds
    the matching REST API by name prefix/suffix.  Returns the full base URL
    including the stage path, or None if resolution fails.
    """
    prefix = suffix = ""
    if _SYNDICATE_CONFIG.exists():
        content = _SYNDICATE_CONFIG.read_text(encoding="utf-8")
        prefix = _extract_yml_value(content, "resources_prefix") or ""
        suffix = _extract_yml_value(content, "resources_suffix") or ""

    try:
        apigw = session.client("apigateway", region_name=AWS_REGION)
        position = None
        while True:
            kwargs: dict = {"limit": 500}
            if position:
                kwargs["position"] = position
            resp = apigw.get_rest_apis(**kwargs)
            for api in resp.get("items", []):
                name = api.get("name", "")
                if prefix and not name.startswith(prefix):
                    continue
                if suffix and not name.endswith(suffix):
                    continue
                api_id = api["id"]
                return (
                    f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{_STAGE}"
                )
            position = resp.get("position")
            if not position:
                break
    except Exception as exc:
        print(f"  ⚠ API Gateway lookup failed: {exc}")

    return None


def _resolve_table(dyn_client, alias: str) -> str | None:
    """Return the real DynamoDB table name for alias, or None if not found.

    Resolution order:
    1. alias as-is
    2. {prefix}{lookup}{suffix} where lookup comes from syndicate_aliases.yml
    3. fuzzy list_tables fallback
    """
    prefix = suffix = ""
    if _SYNDICATE_CONFIG.exists():
        content = _SYNDICATE_CONFIG.read_text(encoding="utf-8")
        prefix = _extract_yml_value(content, "resources_prefix") or ""
        suffix = _extract_yml_value(content, "resources_suffix") or ""

    # Build lookup name from aliases file (e.g. waiter_report_table → waiter_report).
    lookup = alias
    if _SYNDICATE_ALIASES.exists():
        for line in _SYNDICATE_ALIASES.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or ": " not in line:
                continue
            key, value = line.split(": ", 1)
            if key.strip() == f"{alias}_table":
                lookup = value.strip().strip('"').strip("'")
                break

    candidates = [lookup, f"{prefix}{lookup}{suffix}"]
    for candidate in dict.fromkeys(candidates):  # deduplicate, preserve order
        try:
            dyn_client.describe_table(TableName=candidate)
            return candidate
        except ClientError:
            pass

    # Fuzzy list_tables fallback.
    try:
        for name in dyn_client.list_tables().get("TableNames", []):
            if alias in name:
                return name
    except ClientError:
        pass

    return None


# ── DynamoDB snapshot helpers ─────────────────────────────────────────────────


def _dec_to_float(value):
    """Recursively convert Decimal to float in a dict."""
    if isinstance(value, dict):
        return {k: _dec_to_float(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dec_to_float(v) for v in value]
    if isinstance(value, Decimal):
        return float(value)
    return value


def _snap_waiter_report(table, waiter_id: str, period_start: str) -> dict | None:
    """Query waiter_period_index GSI and return the current report row as a plain dict."""
    resp = table.query(
        IndexName="waiter_period_index",
        KeyConditionExpression=(
            Key("waiter_id").eq(waiter_id) & Key("report_period_start").eq(period_start)
        ),
        Limit=1,
    )
    items = resp.get("Items", [])
    return _dec_to_float(items[0]) if items else None


def _snap_location_report(table, location_id: str, period_start: str) -> dict | None:
    """Query location_period_index GSI and return the current report row as a plain dict."""
    resp = table.query(
        IndexName="location_period_index",
        KeyConditionExpression=(
            Key("location_id").eq(location_id)
            & Key("report_period_start").eq(period_start)
        ),
        Limit=1,
    )
    items = resp.get("Items", [])
    return _dec_to_float(items[0]) if items else None


def _all_waiter_periods(table, waiter_id: str) -> list[dict]:
    """Return every waiter_report row for a waiter, across all periods."""
    resp = table.query(
        IndexName="waiter_period_index",
        KeyConditionExpression=Key("waiter_id").eq(waiter_id),
    )
    return [_dec_to_float(i) for i in resp.get("Items", [])]


def _all_location_periods(table, location_id: str) -> list[dict]:
    """Return every location_report row for a location, across all periods."""
    resp = table.query(
        IndexName="location_period_index",
        KeyConditionExpression=Key("location_id").eq(location_id),
    )
    return [_dec_to_float(i) for i in resp.get("Items", [])]


def _dump_entity_periods(label: str, rows: list[dict], fields: list[str]) -> None:
    """Print every period row for an entity so a wrong-week landing is obvious.

    This is the diagnostic shown when a report assertion fails: it reveals which
    ``report_period_start`` each value actually landed in, making it immediately
    clear when (for example) a feedback was attributed to a different ISO week
    than the one the test polls.
    """
    print(f"  {_YELLOW}↳ diagnostics — all {label} rows by period:{_RESET}")
    if not rows:
        print(f"    {_DIM}(no rows found for this entity in any period){_RESET}")
        return
    for row in sorted(rows, key=lambda r: r.get("report_period_start", "")):
        period = row.get("report_period_start", "?")
        vals = "  ".join(f"{f}={_fmt(row.get(f))}" for f in fields)
        print(f"    {_CYAN}{period}{_RESET}  {vals}")


# ── Polling ───────────────────────────────────────────────────────────────────


def _reports_differ(a: dict | None, b: dict | None, fields: list[str]) -> bool:
    """Return True if any tracked field value differs between a and b."""
    if (a is None) != (b is None):
        return True
    if a is None:
        return False
    return any(a.get(f) != b.get(f) for f in fields)


def _poll_until_changed(
    snap_fn,
    before: dict | None,
    fields: list[str],
    timeout: int = 15,
    interval: float = 1.0,
) -> tuple[dict | None, float]:
    """Poll snap_fn() until a tracked field changes or timeout expires.

    Returns (latest_snapshot, elapsed_seconds).
    """
    deadline = time.monotonic() + timeout
    elapsed = 0.0
    print(f"  {_DIM}Polling DynamoDB", end="", flush=True)
    while time.monotonic() < deadline:
        time.sleep(interval)
        elapsed += interval
        after = snap_fn()
        print(".", end="", flush=True)
        if _reports_differ(before, after, fields):
            print(f"  changed after {elapsed:.0f}s{_RESET}")
            return after, elapsed
    print(f"  timeout after {timeout}s{_RESET}")
    return snap_fn(), float(timeout)


# ── Diff display ──────────────────────────────────────────────────────────────


def _fmt(v) -> str:
    """Format a field value for display."""
    if v is None:
        return f"{_DIM}null{_RESET}"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _show_report_snapshot(label: str, snap: dict | None, fields: list[str]) -> None:
    """Print current values of tracked fields for a report."""
    print(f"  {_CYAN}{label}{_RESET}")
    if snap is None:
        print(f"    {_DIM}(no record for this period){_RESET}")
        return
    for f in fields:
        v = snap.get(f)
        print(f"    {f:<40} {_fmt(v)}")


def _show_diff(
    label: str,
    before: dict | None,
    after: dict | None,
    fields: list[str],
) -> bool:
    """Print a colored before→after diff.  Returns True if any field changed."""
    print(f"  {_CYAN}{_BOLD}{label}{_RESET}")
    changed = False
    for f in fields:
        old = before.get(f) if before else None
        new = after.get(f) if after else None
        if old == new:
            continue
        changed = True
        if old is None and new is not None:
            color = _YELLOW
            arrow = f"{_fmt(old)} → {color}{_fmt(new)}{_RESET}  {_YELLOW}(new){_RESET}"
        elif isinstance(new, (int, float)) and isinstance(old, (int, float)):
            delta = new - old
            color = _GREEN if delta > 0 else _RED
            pct = f"  {color}({delta:+.4g}){_RESET}"
            arrow = f"{_fmt(old)} → {color}{_fmt(new)}{_RESET}{pct}"
        else:
            color = _YELLOW
            arrow = f"{_fmt(old)} → {color}{_fmt(new)}{_RESET}"
        print(f"    {f:<40} {arrow}")
    if not changed:
        print(f"    {_DIM}(no changes in tracked fields){_RESET}")
    return changed


# ── Token + ID loading ────────────────────────────────────────────────────────


def _load_tokens() -> dict[str, str]:
    """Read access tokens from tokens.json keyed by email."""
    if not _TOKENS_FILE.exists():
        print(f"{_RED}  ERROR: tokens.json not found at {_TOKENS_FILE}{_RESET}")
        print("  Run quick_seed.py first.")
        sys.exit(1)
    raw = json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
    return {email: data["access_token"] for email, data in raw.items()}


def _load_ids() -> dict:
    """Read seeded entity IDs from ids.json."""
    if not _IDS_FILE.exists():
        print(f"{_RED}  ERROR: ids.json not found at {_IDS_FILE}{_RESET}")
        print("  Run quick_seed.py first.")
        sys.exit(1)
    return json.loads(_IDS_FILE.read_text(encoding="utf-8"))


# ── HTTP helpers ──────────────────────────────────────────────────────────────


def _print_response(resp: requests.Response) -> None:
    """Pretty-print an HTTP response with a coloured status line."""
    ok = resp.status_code < 400
    color = _GREEN if ok else _RED
    print(f"  Status : {color}{resp.status_code} {resp.reason}{_RESET}")
    print(f"  Method : {resp.request.method}  {resp.url}")
    try:
        body = resp.json()
        print(f"  Body   :\n{json.dumps(body, indent=4)}")
    except Exception:
        print(f"  Body   : {resp.text[:600]}")


def _req(
    method: str,
    path: str,
    token: str,
    body: dict | None = None,
    label: str = "",
) -> requests.Response:
    """Send an authenticated HTTP request and pretty-print the result."""
    print(f"\n{SEP}")
    print(f"  {label}")
    print(SEP)
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if body:
        print(f"  Body   : {json.dumps(body)}\n")
    resp = requests.request(method, url, headers=headers, json=body, timeout=30)
    _print_response(resp)
    return resp


def _find_airport_table1_slots(
    location_id: str, date: str, token: str, need: int = 2
) -> list[dict]:
    """Return the first ``need`` free slots for Airport table 1 on ``date``.

    Queries the /bookings/tables availability endpoint (Cognito-authorized) and
    extracts table 1's available_slots, mirroring the original test_endpoints.py.
    """
    url = BASE_URL.rstrip("/") + "/bookings/tables"
    params = {"location_id": location_id, "date": date, "guests_number": 2}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
    except Exception as exc:
        print(f"{_RED}  ERROR during slot discovery: {exc}{_RESET}")
        return []

    if resp.status_code != 200:
        print(f"{_RED}  ERROR: /bookings/tables returned {resp.status_code}{_RESET}")
        try:
            print(f"  Body: {json.dumps(resp.json(), indent=2)}")
        except Exception:
            print(f"  Body: {resp.text[:300]}")
        return []

    for table in resp.json().get("tables", []):
        if table.get("table_number") == 1:
            return table.get("available_slots", [])[:need]

    print(f"{_RED}  ERROR: Airport table 1 not found in availability response{_RESET}")
    return []


# ── Assertion tracker ─────────────────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []
_pending_retries: list[tuple[int, object, object]] = []


def _assert(label: str, condition: bool, reason: str = "") -> bool:
    """Record a pass/fail result and print inline status."""
    _results.append((label, condition, reason))
    mark = f"{_GREEN}✓ PASS{_RESET}" if condition else f"{_RED}✗ FAIL{_RESET}"
    note = f"  {_DIM}{reason}{_RESET}" if reason and not condition else ""
    print(f"  {mark}  {label}{note}")
    return condition


def _assert_dynamo(label: str, check_fn, reason: str = "", diagnose=None) -> bool:
    """Assert a DynamoDB condition; queues a re-check at end of run if it fails.

    Args:
        label: Assertion label recorded in the summary.
        check_fn: Zero-arg callable returning the boolean condition.
        reason: Hint shown next to a failure.
        diagnose: Optional zero-arg callable that prints extra context (e.g. all
            report rows by period). Invoked immediately on failure and again if
            the assertion is still failing after the final retry.

    """
    ok = check_fn()
    idx = len(_results)
    _assert(label, ok, reason)
    if not ok:
        if diagnose is not None:
            diagnose()
        _pending_retries.append((idx, check_fn, diagnose))
    return ok


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """Run all SQS trigger tests automatically and display DynamoDB diffs."""
    _results.clear()
    _pending_retries.clear()

    # ── 0. Refresh Cognito tokens (expire after 1 hour) ───────────────────
    print(f"\n{DSEP}")
    print("  SQS TRIGGER TESTS  (automated)")
    print(DSEP)

    print("▶ Refreshing Cognito tokens...")
    try:
        import generate_tokens as _gt

        _gt.generate_all()
        print("  ✓ Tokens refreshed")
    except Exception as exc:
        print(f"  ⚠ Token refresh failed (will use cached): {exc}")

    # ── 1. Load tokens and IDs ─────────────────────────────────────────────
    tokens = _load_tokens()
    IDS = _load_ids()

    def _tok(email: str) -> str:
        t = tokens.get(email, "")
        if not t:
            print(f"{_RED}  WARNING: no token for {email}{_RESET}")
        return t

    # max@example.com — Airport table-1 waiter (0 seeded orders/feedback).
    # kate@example.com — customer with no seeded reservations (clean slate).
    TOKEN_MAX = _tok("max@example.com")
    TOKEN_KATE = _tok("kate@example.com")

    # ── 2. Connect to AWS ──────────────────────────────────────────────────
    print("▶ Loading AWS credentials...")
    creds = _load_syndicate_credentials()
    if creds:
        print("  ✓ Loaded from syndicate config")
        session = boto3.session.Session(region_name=AWS_REGION, **creds)
    else:
        print("  ✓ Using environment / profile credentials")
        session = boto3.session.Session(region_name=AWS_REGION)

    try:
        identity = session.client("sts").get_caller_identity()
        print(f"  ✓ Account: {identity['Account']}  |  {identity['Arn']}")
    except (ClientError, NoCredentialsError) as e:
        print(f"{_RED}  ✗ AWS credentials invalid: {e}{_RESET}")
        return 1

    print("▶ Resolving API Gateway URL...")
    global BASE_URL
    resolved_url = _resolve_base_url(session)
    if resolved_url:
        BASE_URL = resolved_url
        print(f"  ✓ {BASE_URL}")
    else:
        print(f"{_RED}  ✗ Could not resolve API Gateway URL automatically{_RESET}")
        return 1

    dyn_client = session.client("dynamodb", region_name=AWS_REGION)
    dyn = session.resource("dynamodb", region_name=AWS_REGION)

    print("▶ Resolving report table names...")
    waiter_report_name = _resolve_table(dyn_client, "waiter_report")
    location_report_name = _resolve_table(dyn_client, "location_report")
    if not waiter_report_name or not location_report_name:
        print(f"{_RED}  ✗ Could not resolve report tables{_RESET}")
        return 1
    print(f"  ✓ waiter_report   → {waiter_report_name}")
    print(f"  ✓ location_report → {location_report_name}")

    waiter_report_tbl = dyn.Table(waiter_report_name)
    location_report_tbl = dyn.Table(location_report_name)

    # ── 3. Resolve fixed test data (Airport + max, mirrors test_endpoints.py)
    airport_loc_id = IDS["locations"]["airport"]
    airport_dish_id = IDS["dishes"]["airport"]["Grilled Chicken Wrap"]
    max_waiter_id = IDS["waiters"]["max@example.com"]

    # New bookings target tomorrow: today's Airport slots (08:00 UTC) may be in
    # the past, and slots are seeded 7+ days ahead.
    booking_date = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    _date_obj = datetime.fromisoformat(booking_date).date()
    _PERIOD_START = (_date_obj - timedelta(days=_date_obj.weekday())).isoformat()
    _PERIOD_END = (
        _date_obj - timedelta(days=_date_obj.weekday()) + timedelta(days=6)
    ).isoformat()

    print(f"\n▶ Discovering Airport table-1 slots for {booking_date} ...")
    slots = _find_airport_table1_slots(airport_loc_id, booking_date, TOKEN_KATE, need=2)
    if len(slots) < 2:
        print(
            f"{_RED}  ✗ FATAL: need ≥ 2 free slots at Airport table 1 on "
            f"{booking_date}.{_RESET}\n"
            "  Re-run quick_seed.py to refresh slot data, or pick a date that "
            "still has free slots.\n"
        )
        return 1
    slot_a = slots[0]  # full lifecycle: CREATED → IN_PROGRESS → order → FINISHED
    slot_b = slots[1]  # CREATED → CANCELLED demo
    print("  ✓ found 2 free slots")

    print(f"\n▶ Test data (report period {_PERIOD_START} → {_PERIOD_END})")
    print(f"  Location : Airport          ({airport_loc_id})")
    print(f"  Waiter   : max@example.com   ({max_waiter_id})")
    print("  Customer : kate@example.com  (no seeded reservations)")
    print(f"  Date     : {booking_date}")
    print(f"  Slot A   : {slot_a['start_time']}  →  {slot_a['end_time']}")
    print(f"  Slot B   : {slot_b['start_time']}  →  {slot_b['end_time']}")

    def snap_waiter():
        return _snap_waiter_report(waiter_report_tbl, max_waiter_id, _PERIOD_START)

    def snap_location():
        return _snap_location_report(location_report_tbl, airport_loc_id, _PERIOD_START)

    def diag_waiter():
        """Print every waiter-report period row for max — on assertion failure."""
        _dump_entity_periods(
            "waiter-report (max)",
            _all_waiter_periods(waiter_report_tbl, max_waiter_id),
            _WAITER_FIELDS,
        )

    def diag_location():
        """Print every location-report period row for airport — on assertion failure."""
        _dump_entity_periods(
            "location-report (airport)",
            _all_location_periods(location_report_tbl, airport_loc_id),
            _LOCATION_FIELDS,
        )

    # ── 4. Baseline snapshots ──────────────────────────────────────────────
    print("\n▶ Baseline snapshots")
    cur_waiter = snap_waiter()
    cur_location = snap_location()
    _show_report_snapshot(
        "waiter-report  (max@example.com)", cur_waiter, _WAITER_FIELDS
    )
    _show_report_snapshot("location-report (airport)", cur_location, _LOCATION_FIELDS)

    # ── T-1: kate creates reservation at Airport table 1 (slot A) ──────────
    #         SQS CREATED — ignored by both report services.
    r1 = _req(
        "POST",
        "/bookings/client",
        TOKEN_KATE,
        body={
            "locationId": airport_loc_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_a["start_time"],
            "timeTo": slot_a["end_time"],
        },
        label=(
            "T-1 | kate creates reservation at Airport table 1\n"
            "  SQS      : CREATED — ignored by both report services\n"
            "  Expected : 200/201  |  reports UNCHANGED"
        ),
    )
    _assert("T-1: HTTP 200/201", r1.status_code in (200, 201), f"got {r1.status_code}")
    res_id: str | None = None
    if r1.status_code < 400:
        res_id = r1.json().get("reservationId") or r1.json().get("id")
        if res_id:
            print(f"\n  >> Captured reservation ID: {res_id}")
    if not res_id:
        print(f"{_RED}  ✗ No reservation ID — cannot continue lifecycle tests.{_RESET}")
        return _summary()

    time.sleep(3)
    _bw1, _bl1 = cur_waiter, cur_location
    _assert_dynamo(
        "T-1: reports unchanged after CREATED",
        lambda bw=_bw1, bl=_bl1: (
            not _reports_differ(bw, snap_waiter(), _WAITER_FIELDS)
            and not _reports_differ(bl, snap_location(), _LOCATION_FIELDS)
        ),
        "CREATED should be ignored",
    )

    # ── T-2: max moves RESERVED → IN_PROGRESS ──────────────────────────────
    #         SQS UPDATED — ignored by both report services.
    r2 = _req(
        "PUT",
        f"/bookings/waiter/{res_id}",
        TOKEN_MAX,
        body={"status": "In Progress"},
        label=(
            "T-2 | max moves reservation  RESERVED → IN_PROGRESS\n"
            "  SQS      : UPDATED — ignored by both report services\n"
            "  Expected : 200  |  reports UNCHANGED"
        ),
    )
    _assert("T-2: HTTP 200", r2.status_code == 200, f"got {r2.status_code}")
    time.sleep(3)
    _bw2, _bl2 = cur_waiter, cur_location
    _assert_dynamo(
        "T-2: reports unchanged after UPDATED",
        lambda bw=_bw2, bl=_bl2: (
            not _reports_differ(bw, snap_waiter(), _WAITER_FIELDS)
            and not _reports_differ(bl, snap_location(), _LOCATION_FIELDS)
        ),
        "UPDATED should be ignored",
    )

    # ── T-3: max creates an order (no SQS event; drives revenue at FINISHED)
    r3 = _req(
        "POST",
        "/orders",
        TOKEN_MAX,
        body={
            "reservationId": res_id,
            "items": [{"dishId": airport_dish_id, "quantity": 2}],
        },
        label=(
            "T-3 | max creates an order  (2× Grilled Chicken Wrap)\n"
            "  SQS      : none\n"
            "  Expected : 200/201  |  counted in revenue when T-4 fires"
        ),
    )
    _assert("T-3: HTTP 200/201", r3.status_code in (200, 201), f"got {r3.status_code}")

    # ── T-4: max marks reservation FINISHED ────────────────────────────────
    #         SQS FINISHED → waiter-report + location-report RECALCULATED.
    r4 = _req(
        "PUT",
        f"/bookings/waiter/{res_id}",
        TOKEN_MAX,
        body={"status": "Finished"},
        label=(
            "T-4 | max marks reservation  IN_PROGRESS → FINISHED\n"
            "  SQS      : FINISHED → waiter-report + location-report RECALCULATED\n"
            "  Expected : 200\n"
            "  Watch    : orders_processed +1 (waiter & location), revenue +dish×2"
        ),
    )
    _assert("T-4: HTTP 200", r4.status_code == 200, f"got {r4.status_code}")

    print(f"\n  {_BOLD}Waiting for waiter-report update (max 15s)...{_RESET}")
    _bw4 = cur_waiter
    new_waiter, _ = _poll_until_changed(snap_waiter, _bw4, _WAITER_FIELDS)
    print()
    _show_diff("waiter-report (max):", _bw4, new_waiter, _WAITER_FIELDS)
    _assert_dynamo(
        "T-4: waiter orders_processed increased",
        lambda bw=_bw4: (
            (snap_waiter() or {}).get("orders_processed", 0)
            > (bw or {}).get("orders_processed", 0)
        ),
        "orders_processed should increase",
        diagnose=diag_waiter,
    )
    cur_waiter = new_waiter

    print(f"\n  {_BOLD}Waiting for location-report update (max 15s)...{_RESET}")
    _bl4 = cur_location
    new_location, _ = _poll_until_changed(snap_location, _bl4, _LOCATION_FIELDS)
    print()
    _show_diff("location-report (airport):", _bl4, new_location, _LOCATION_FIELDS)
    _assert_dynamo(
        "T-4: location orders_processed increased",
        lambda bl=_bl4: (
            (snap_location() or {}).get("orders_processed", 0)
            > (bl or {}).get("orders_processed", 0)
        ),
        "orders_processed should increase",
        diagnose=diag_location,
    )
    _assert_dynamo(
        "T-4: location revenue increased",
        lambda bl=_bl4: (
            (snap_location() or {}).get("revenue", 0) > (bl or {}).get("revenue", 0)
        ),
        "revenue should increase",
        diagnose=diag_location,
    )
    cur_location = new_location

    # ── T-5: kate submits CULINARY feedback (rating 5) ─────────────────────
    #         SQS CULINARY CREATED → location-report RECALCULATED.
    r5 = _req(
        "POST",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "Excellent flavors and beautifully presented.",
            "rating": 5,
            "type": "culinary",
        },
        label=(
            "T-5 | kate submits CULINARY feedback  (rating 5)\n"
            "  SQS      : CULINARY CREATED → location-report RECALCULATED\n"
            "  Expected : 201  |  cuisine_feedback_count +1"
        ),
    )
    _assert("T-5: HTTP 201", r5.status_code == 201, f"got {r5.status_code}")

    print(f"\n  {_BOLD}Waiting for location-report update (max 15s)...{_RESET}")
    _bl5 = cur_location
    new_location, _ = _poll_until_changed(snap_location, _bl5, _LOCATION_FIELDS)
    print()
    _show_diff("location-report (airport):", _bl5, new_location, _LOCATION_FIELDS)
    _assert_dynamo(
        "T-5: cuisine_feedback_count increased",
        lambda bl=_bl5: (
            (snap_location() or {}).get("cuisine_feedback_count", 0)
            > (bl or {}).get("cuisine_feedback_count", 0)
        ),
        "cuisine_feedback_count should be higher",
        diagnose=diag_location,
    )
    cur_location = new_location

    # ── T-6: kate submits SERVICE feedback (rating 4) ──────────────────────
    #         SQS SERVICE CREATED → waiter-report RECALCULATED.
    r6 = _req(
        "POST",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "Attentive and professional throughout the visit.",
            "rating": 4,
            "type": "service",
        },
        label=(
            "T-6 | kate submits SERVICE feedback  (rating 4)\n"
            "  SQS      : SERVICE CREATED → waiter-report RECALCULATED\n"
            "  Expected : 201  |  service_feedback_count +1"
        ),
    )
    _assert("T-6: HTTP 201", r6.status_code == 201, f"got {r6.status_code}")

    print(f"\n  {_BOLD}Waiting for waiter-report update (max 15s)...{_RESET}")
    _bw6 = cur_waiter
    new_waiter, _ = _poll_until_changed(snap_waiter, _bw6, _WAITER_FIELDS)
    print()
    _show_diff("waiter-report (max):", _bw6, new_waiter, _WAITER_FIELDS)
    _assert_dynamo(
        "T-6: service_feedback_count increased",
        lambda bw=_bw6: (
            (snap_waiter() or {}).get("service_feedback_count", 0)
            > (bw or {}).get("service_feedback_count", 0)
        ),
        "service_feedback_count should be higher",
        diagnose=diag_waiter,
    )
    cur_waiter = new_waiter

    # ── T-7: Duplicate CULINARY → 409 (rejected before publish) ────────────
    r7 = _req(
        "POST",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "Trying a second culinary rating.",
            "rating": 3,
            "type": "culinary",
        },
        label=(
            "T-7 | kate submits duplicate CULINARY feedback\n"
            "  SQS      : none — rejected before publish\n"
            "  Expected : 409  |  location-report UNCHANGED"
        ),
    )
    _assert("T-7: HTTP 409", r7.status_code == 409, f"got {r7.status_code}")
    time.sleep(3)
    _bl7 = cur_location
    _assert_dynamo(
        "T-7: location-report unchanged",
        lambda bl=_bl7: not _reports_differ(bl, snap_location(), _LOCATION_FIELDS),
        "duplicate should not update report",
    )

    # ── T-8: Duplicate SERVICE → 409 (rejected before publish) ─────────────
    r8 = _req(
        "POST",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "Trying a second service rating.",
            "rating": 5,
            "type": "service",
        },
        label=(
            "T-8 | kate submits duplicate SERVICE feedback\n"
            "  SQS      : none — rejected before publish\n"
            "  Expected : 409  |  waiter-report UNCHANGED"
        ),
    )
    _assert("T-8: HTTP 409", r8.status_code == 409, f"got {r8.status_code}")
    time.sleep(3)
    _bw8 = cur_waiter
    _assert_dynamo(
        "T-8: waiter-report unchanged",
        lambda bw=_bw8: not _reports_differ(bw, snap_waiter(), _WAITER_FIELDS),
        "duplicate should not update report",
    )

    # ── T-9: kate creates a 2nd reservation (slot B) → CREATED (ignored) ───
    cur_location = snap_location()
    r9 = _req(
        "POST",
        "/bookings/client",
        TOKEN_KATE,
        body={
            "locationId": airport_loc_id,
            "tableNumber": 1,
            "date": booking_date,
            "guestsNumber": 2,
            "timeFrom": slot_b["start_time"],
            "timeTo": slot_b["end_time"],
        },
        label=(
            "T-9 | kate creates a second reservation at Airport table 1\n"
            "  SQS      : CREATED — ignored by both report services\n"
            "  Expected : 200/201  |  reports UNCHANGED"
        ),
    )
    _assert("T-9: HTTP 200/201", r9.status_code in (200, 201), f"got {r9.status_code}")
    res_id_b: str | None = None
    if r9.status_code < 400:
        res_id_b = r9.json().get("reservationId") or r9.json().get("id")
        if res_id_b:
            print(f"\n  >> Captured reservation ID: {res_id_b}")
    time.sleep(3)
    _bl9 = cur_location
    _assert_dynamo(
        "T-9: location-report unchanged after CREATED",
        lambda bl=_bl9: not _reports_differ(bl, snap_location(), _LOCATION_FIELDS),
        "CREATED should be ignored",
    )

    # ── T-10: kate cancels the 2nd reservation → CANCELLED (ignored) ───────
    if res_id_b:
        cur_location = snap_location()
        r10 = _req(
            "DELETE",
            f"/bookings/client/{res_id_b}/cancel",
            TOKEN_KATE,
            label=(
                "T-10 | kate cancels the second reservation\n"
                "  SQS      : CANCELLED — ignored by both report services\n"
                "  Expected : 200/204  |  reports UNCHANGED"
            ),
        )
        _assert(
            "T-10: HTTP 200/204",
            r10.status_code in (200, 204),
            f"got {r10.status_code}",
        )
        time.sleep(3)
        _bl10 = cur_location
        _assert_dynamo(
            "T-10: reports unchanged after CANCELLED",
            lambda bl=_bl10: not _reports_differ(bl, snap_location(), _LOCATION_FIELDS),
            "CANCELLED should be ignored",
        )
    else:
        print(f"\n{SEP}\n  T-10 — SKIPPED (no reservation ID from T-9)\n{SEP}")
        _assert("T-10: HTTP 200/204", False, "skipped")
        _assert("T-10: reports unchanged after CANCELLED", False, "skipped")

    # ── T-11: kate edits her SERVICE feedback (4 → 1) ──────────────────────
    #          SQS SERVICE EDITED → waiter-report RECALCULATED (avg drops).
    cur_waiter = snap_waiter()
    r11 = _req(
        "PUT",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "On reflection the service was slow.",
            "rating": 1,
            "type": "service",
        },
        label=(
            "T-11 | kate edits SERVICE feedback  (rating 4 → 1)\n"
            "  SQS      : SERVICE EDITED → waiter-report RECALCULATED\n"
            "  Expected : 200  |  avg_service_feedback DROPS, count unchanged"
        ),
    )
    _assert("T-11: HTTP 200", r11.status_code == 200, f"got {r11.status_code}")

    print(f"\n  {_BOLD}Waiting for waiter-report update (max 15s)...{_RESET}")
    _bw11 = cur_waiter
    new_waiter, _ = _poll_until_changed(snap_waiter, _bw11, _WAITER_FIELDS)
    print()
    _show_diff("waiter-report (max):", _bw11, new_waiter, _WAITER_FIELDS)
    _assert_dynamo(
        "T-11: avg_service_feedback decreased after edit",
        lambda bw=_bw11: (
            (snap_waiter() or {}).get("avg_service_feedback", 0)
            < (bw or {}).get("avg_service_feedback", 5)
        ),
        "edited rating 1 should lower the average",
        diagnose=diag_waiter,
    )
    cur_waiter = new_waiter

    # ── T-12: kate edits her CULINARY feedback (5 → 1) ─────────────────────
    #          SQS CULINARY EDITED → location-report RECALCULATED (avg drops).
    cur_location = snap_location()
    r12 = _req(
        "PUT",
        "/feedbacks",
        TOKEN_KATE,
        body={
            "reservation_id": res_id,
            "comment": "On reflection the food was disappointing.",
            "rating": 1,
            "type": "culinary",
        },
        label=(
            "T-12 | kate edits CULINARY feedback  (rating 5 → 1)\n"
            "  SQS      : CULINARY EDITED → location-report RECALCULATED\n"
            "  Expected : 200  |  avg_cuisine_feedback DROPS, count unchanged"
        ),
    )
    _assert("T-12: HTTP 200", r12.status_code == 200, f"got {r12.status_code}")

    print(f"\n  {_BOLD}Waiting for location-report update (max 15s)...{_RESET}")
    _bl12 = cur_location
    new_location, _ = _poll_until_changed(snap_location, _bl12, _LOCATION_FIELDS)
    print()
    _show_diff("location-report (airport):", _bl12, new_location, _LOCATION_FIELDS)
    _assert_dynamo(
        "T-12: avg_cuisine_feedback decreased after edit",
        lambda bl=_bl12: (
            (snap_location() or {}).get("avg_cuisine_feedback", 0)
            < (bl or {}).get("avg_cuisine_feedback", 5)
        ),
        "edited rating 1 should lower the average",
        diagnose=diag_location,
    )
    cur_location = new_location

    if _pending_retries:
        print(
            f"\n▶ Re-checking {len(_pending_retries)} failed DynamoDB assertion(s) (waiting 15s)..."
        )
        time.sleep(15)
        recovered = 0
        for idx, check_fn, diagnose in _pending_retries:
            label, _, _ = _results[idx]
            ok = check_fn()
            if ok:
                _results[idx] = (label, True, "passed on retry")
                print(f"  {_GREEN}↺ RECOVERED{_RESET}  {label}")
                recovered += 1
            else:
                print(f"  {_RED}↺ STILL FAILING{_RESET}  {label}")
                if diagnose is not None:
                    diagnose()
        if recovered:
            print(
                f"  {_GREEN}{recovered}/{len(_pending_retries)} recovered on retry{_RESET}"
            )

    return _summary()


def _summary() -> int:
    """Print the final pass/fail summary and return the process exit code."""
    print(f"\n{DSEP}")
    print(f"  {_BOLD}TEST RESULTS{_RESET}")
    print(DSEP)
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    for label, ok, reason in _results:
        mark = f"{_GREEN}✓{_RESET}" if ok else f"{_RED}✗{_RESET}"
        suffix = f"  {_DIM}{reason}{_RESET}" if reason and not ok else ""
        print(f"  {mark}  {label}{suffix}")
    print()
    color = _GREEN if passed == total else _RED
    print(f"  {color}{_BOLD}{passed}/{total} passed{_RESET}")
    print(DSEP + "\n")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

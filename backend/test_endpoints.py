"""Interactive end-to-end test runner for SQS triggers and report generation.

Uses Airport location (0 seeded orders/feedback) and max@example.com (0 seeded
orders_processed) so every SQS-driven change is visible from a zero baseline.

Usage:
    python test_endpoints.py

Tokens are read live from tokens.json.  IDs from ids.json.
Re-run quick_seed.py whenever tokens expire (1 hour).
"""

import json
import pathlib
import sys
from datetime import UTC, datetime, timedelta

import requests

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = "https://enn4j1nwo8.execute-api.eu-west-3.amazonaws.com/api/"
_TOKENS_FILE = pathlib.Path(__file__).parent / "tokens.json"
_IDS_FILE = pathlib.Path(__file__).parent / "ids.json"


# ── Loaders ───────────────────────────────────────────────────────────────────


def _load_tokens() -> dict[str, str]:
    """Read access tokens from tokens.json keyed by email."""
    if not _TOKENS_FILE.exists():
        print(f"\033[91m  ERROR: tokens.json not found at {_TOKENS_FILE}\033[0m")
        print("  Run quick_seed.py first to generate tokens.")
        sys.exit(1)
    raw = json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
    return {email: data["access_token"] for email, data in raw.items()}


def _load_ids() -> dict:
    """Read seeded entity IDs from ids.json."""
    if not _IDS_FILE.exists():
        print(f"\033[91m  ERROR: ids.json not found at {_IDS_FILE}\033[0m")
        print("  Run quick_seed.py first to generate ids.")
        sys.exit(1)
    return json.loads(_IDS_FILE.read_text(encoding="utf-8"))


_TOKENS = _load_tokens()
IDS = _load_ids()


def _tok(email: str) -> str:
    """Look up access token for email; warn if missing."""
    token = _TOKENS.get(email)
    if not token:
        print(f"\033[91m  WARNING: no token found for {email} in tokens.json\033[0m")
        return ""
    return token


# max@example.com — Airport waiter, 0 seeded orders_processed, 0 seeded service feedback
TOKEN_MAX = _tok("max@example.com")

# kate@example.com — customer with no seeded reservations, clean slate throughout
TOKEN_KATE = _tok("kate@example.com")

# ── Fixed IDs ─────────────────────────────────────────────────────────────────

AIRPORT_LOCATION_ID = IDS["locations"]["airport"]
AIRPORT_DISH_ID = IDS["dishes"]["airport"]["Grilled Chicken Wrap"]
MAX_WAITER_ID = IDS["waiters"]["max@example.com"]

# ── Slot discovery ─────────────────────────────────────────────────────────────
#
# Airport table 1, first shift → assigned to max@example.com.
# Today's Airport slots start at 08:00 UTC and may already be in the past, so
# tomorrow is used for all new bookings.  Slots are seeded 7 days ahead.

_TOMORROW = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()


def _find_airport_table1_slots(date: str, need: int = 2) -> list[dict]:
    """Return the first ``need`` free slots for Airport table 1 on ``date``."""
    url = f"{BASE_URL}/bookings/tables"
    params = {"location_id": AIRPORT_LOCATION_ID, "date": date, "guests_number": 2}
    try:
        resp = requests.get(url, params=params, timeout=30)
    except Exception as exc:
        print(f"\033[91m  ERROR during slot discovery: {exc}\033[0m")
        return []

    if resp.status_code != 200:
        print(f"\033[91m  ERROR: /bookings/tables returned {resp.status_code}\033[0m")
        try:
            print(f"  Body: {json.dumps(resp.json(), indent=2)}")
        except Exception:
            print(f"  Body: {resp.text[:300]}")
        return []

    for table in resp.json().get("tables", []):
        if table.get("table_number") == 1:
            return table.get("available_slots", [])[:need]

    print("\033[91m  ERROR: Airport table 1 not found in availability response\033[0m")
    return []


print(f"\n  Discovering Airport table-1 slots for {_TOMORROW} …", end=" ", flush=True)
_SLOTS = _find_airport_table1_slots(_TOMORROW, need=2)

if len(_SLOTS) < 2:
    print(
        f"\n\033[91m  FATAL: Need ≥ 2 free slots at Airport table 1 on {_TOMORROW}.\033[0m\n"
        "  Options:\n"
        "    • Re-run quick_seed.py to refresh slot data\n"
        "    • Set _TOMORROW to a date that still has free slots\n"
    )
    sys.exit(1)

print("OK")

_SLOT_A = _SLOTS[
    0
]  # full lifecycle: CREATED → IN_PROGRESS → order → FINISHED → feedbacks
_SLOT_B = _SLOTS[1]  # CREATED → CANCELLED demo

# ── Helpers ───────────────────────────────────────────────────────────────────

SEP = "─" * 70
_context: dict = {}


def _header(label: str) -> None:
    """Print a decorated test section header."""
    print(f"\n{SEP}")
    print(f"  {label}")
    print(SEP)


def _print_response(resp: requests.Response) -> None:
    """Pretty-print an HTTP response with a coloured status line."""
    ok = resp.status_code < 400
    color = "\033[92m" if ok else "\033[91m"
    reset = "\033[0m"
    print(f"  Status : {color}{resp.status_code} {resp.reason}{reset}")
    print(f"  Method : {resp.request.method}  {resp.url}")
    try:
        body = resp.json()
        print(f"  Body   :\n{json.dumps(body, indent=4)}")
    except Exception:
        print(f"  Body   : {resp.text[:600]}")
    if not ok:
        print("\033[91m  ^ ERROR — check the response above\033[0m")


def _wait() -> None:
    """Pause and wait for Enter; Ctrl+C exits cleanly."""
    try:
        input(f"\n  {'[Press Enter for next test, Ctrl+C to quit]':^70}\n")
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)


def _req(
    method: str,
    path: str,
    token: str,
    body: dict | None = None,
    label: str = "",
) -> requests.Response:
    """Send an authenticated HTTP request and pretty-print the result."""
    _header(label)
    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if body:
        print(f"  Body   : {json.dumps(body)}\n")
    resp = requests.request(method, url, headers=headers, json=body, timeout=30)
    _print_response(resp)
    return resp


def _skip(label: str, reason: str) -> None:
    """Print a skip notice for a test that cannot run."""
    print(f"\n{SEP}\n  {label} — SKIPPED ({reason})\n{SEP}")


# ── Tests ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run all SQS trigger tests interactively, pausing between each step."""
    print(f"\n{'═' * 70}")
    print("  SQS TRIGGER TESTS")
    print(f"{'═' * 70}")
    print(f"  Location : Airport   ({AIRPORT_LOCATION_ID})")
    print(f"  Waiter   : max@example.com  ({MAX_WAITER_ID})")
    print("  Customer : kate@example.com  (no seeded reservations)")
    print(f"  Date     : {_TOMORROW}")
    print(f"  Slot A   : {_SLOT_A['start_time']}  →  {_SLOT_A['end_time']}")
    print(f"  Slot B   : {_SLOT_B['start_time']}  →  {_SLOT_B['end_time']}")
    print()
    print("  Airport and max both start at 0 orders / 0 feedback.")
    print("  Every SQS-driven change is visible from a zero baseline.")
    print("  Tokens expire 1 h after seeding. Re-run quick_seed.py on 401s.")

    # ─────────────────────────────────────────────────────────────────────────
    # T-1  kate books Airport table 1, slot A
    #      SQS: CREATED → ignored by both report services (no report change)
    # ─────────────────────────────────────────────────────────────────────────
    create_resp = _req(
        method="POST",
        path="/bookings/client",
        token=TOKEN_KATE,
        body={
            "locationId": AIRPORT_LOCATION_ID,
            "tableNumber": 1,
            "date": _TOMORROW,
            "guestsNumber": 2,
            "timeFrom": _SLOT_A["start_time"],
            "timeTo": _SLOT_A["end_time"],
        },
        label=(
            f"T-1 | kate creates reservation at Airport table 1\n"
            f"  Slot     : {_SLOT_A['start_time']} → {_SLOT_A['end_time']}\n"
            f"  SQS      : CREATED — ignored by both report services\n"
            f"  Expected : 200  |  waiter-report and location-report UNCHANGED"
        ),
    )

    res_id: str | None = None
    if create_resp.status_code < 400:
        data = create_resp.json()
        res_id = data.get("reservationId") or data.get("id")
        if res_id:
            _context["main_res_id"] = res_id
            print(f"\n  >> Captured reservation ID: {res_id}")
        else:
            print(
                "\033[91m  >> reservationId missing in response — T-2…T-8 will be skipped\033[0m"
            )
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-2  max moves RESERVED → IN_PROGRESS
    #      SQS: UPDATED → ignored by both report services (no report change)
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="PUT",
            path=f"/bookings/waiter/{res_id}",
            token=TOKEN_MAX,
            body={"status": "In Progress"},
            label=(
                "T-2 | max moves reservation  RESERVED → IN_PROGRESS\n"
                "  SQS      : UPDATED — ignored by both report services\n"
                "  Expected : 200  |  reports UNCHANGED"
            ),
        )
    else:
        _skip("T-2", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-3  max creates an order — no SQS event, but drives revenue after FINISHED
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="POST",
            path="/orders",
            token=TOKEN_MAX,
            body={
                "reservationId": res_id,
                "items": [{"dishId": AIRPORT_DISH_ID, "quantity": 2}],
            },
            label=(
                "T-3 | max creates an order  (2× Grilled Chicken Wrap)\n"
                "  SQS      : none\n"
                "  Expected : 201\n"
                "  NOTE     : order is counted in location-report revenue when T-4 fires"
            ),
        )
    else:
        _skip("T-3", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-4  max marks reservation FINISHED
    #      SQS: FINISHED → WaiterReportService + LocationReportService both recalculate
    #      Watch DynamoDB:
    #        waiter-report   (max)     orders_processed      0 → 1
    #        location-report (airport) orders_processed      0 → 1
    #        location-report (airport) revenue               0 → <dish price × 2>
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="PUT",
            path=f"/bookings/waiter/{res_id}",
            token=TOKEN_MAX,
            body={"status": "Finished"},
            label=(
                "T-4 | max marks reservation  IN_PROGRESS → FINISHED\n"
                "  SQS      : FINISHED → waiter-report + location-report RECALCULATED\n"
                "  Expected : 200\n"
                "  Watch DynamoDB:\n"
                "    waiter-report   (max)      orders_processed  0 → 1\n"
                "    location-report (airport)  orders_processed  0 → 1\n"
                "    location-report (airport)  revenue           0 → <dish × 2>"
            ),
        )
    else:
        _skip("T-4", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-5  kate submits CULINARY feedback (rating 5)
    #      SQS: CULINARY CREATED → LocationReportService recalculates airport row
    #      Watch DynamoDB:
    #        location-report (airport) cuisine_feedback_count  0 → 1
    #        location-report (airport) avg_cuisine_feedback    null → 5.0
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="POST",
            path="/feedbacks",
            token=TOKEN_KATE,
            body={
                "reservation_id": res_id,
                "comment": "Excellent flavors and beautifully presented.",
                "rating": 5,
                "type": "culinary",
            },
            label=(
                "T-5 | kate submits CULINARY feedback  (rating 5)\n"
                "  SQS      : CULINARY CREATED → location-report RECALCULATED\n"
                "  Expected : 201\n"
                "  Watch DynamoDB:\n"
                "    location-report (airport)  cuisine_feedback_count  0 → 1\n"
                "    location-report (airport)  avg_cuisine_feedback    null → 5.0"
            ),
        )
    else:
        _skip("T-5", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-6  kate submits SERVICE feedback (rating 4)
    #      SQS: SERVICE CREATED → WaiterReportService recalculates max's row
    #      Watch DynamoDB:
    #        waiter-report (max) service_feedback_count  0 → 1
    #        waiter-report (max) avg_service_feedback    null → 4.0
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="POST",
            path="/feedbacks",
            token=TOKEN_KATE,
            body={
                "reservation_id": res_id,
                "comment": "Attentive and professional throughout the visit.",
                "rating": 4,
                "type": "service",
            },
            label=(
                "T-6 | kate submits SERVICE feedback  (rating 4)\n"
                "  SQS      : SERVICE CREATED → waiter-report RECALCULATED\n"
                "  Expected : 201\n"
                "  Watch DynamoDB:\n"
                "    waiter-report (max)  service_feedback_count  0 → 1\n"
                "    waiter-report (max)  avg_service_feedback    null → 4.0"
            ),
        )
    else:
        _skip("T-6", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-7  Duplicate CULINARY → 409
    #      feedback_id is uuid5(NAMESPACE_URL, "culinary:{res_id}") — deterministic,
    #      so the second attempt collides in DynamoDB before SQS publish.
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="POST",
            path="/feedbacks",
            token=TOKEN_KATE,
            body={
                "reservation_id": res_id,
                "comment": "Trying a second culinary rating.",
                "rating": 3,
                "type": "culinary",
            },
            label=(
                "T-7 | kate submits duplicate CULINARY feedback (same reservation)\n"
                "  SQS      : none — rejected before publish\n"
                "  Expected : 409  |  reports UNCHANGED"
            ),
        )
    else:
        _skip("T-7", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-8  Duplicate SERVICE → 409
    # ─────────────────────────────────────────────────────────────────────────
    if res_id:
        _req(
            method="POST",
            path="/feedbacks",
            token=TOKEN_KATE,
            body={
                "reservation_id": res_id,
                "comment": "Trying a second service rating.",
                "rating": 5,
                "type": "service",
            },
            label=(
                "T-8 | kate submits duplicate SERVICE feedback (same reservation)\n"
                "  SQS      : none — rejected before publish\n"
                "  Expected : 409  |  reports UNCHANGED"
            ),
        )
    else:
        _skip("T-8", "no reservation ID from T-1")
    _wait()

    # ─────────────────────────────────────────────────────────────────────────
    # T-9 / T-10  CREATED → CANCELLED demo
    #      Neither event is processed by the report services.
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{'═' * 70}")
    print("  T-9 / T-10: CREATED → CANCELLED — neither event updates reports")
    print(f"{'═' * 70}")

    create_resp2 = _req(
        method="POST",
        path="/bookings/client",
        token=TOKEN_KATE,
        body={
            "locationId": AIRPORT_LOCATION_ID,
            "tableNumber": 1,
            "date": _TOMORROW,
            "guestsNumber": 2,
            "timeFrom": _SLOT_B["start_time"],
            "timeTo": _SLOT_B["end_time"],
        },
        label=(
            f"T-9 | kate creates a second reservation at Airport table 1\n"
            f"  Slot     : {_SLOT_B['start_time']} → {_SLOT_B['end_time']}\n"
            f"  SQS      : CREATED — ignored by both report services\n"
            f"  Expected : 200  |  reports UNCHANGED"
        ),
    )

    res_id_b: str | None = None
    if create_resp2.status_code < 400:
        data = create_resp2.json()
        res_id_b = data.get("reservationId") or data.get("id")
        if res_id_b:
            _context["cancel_res_id"] = res_id_b
            print(f"\n  >> Captured reservation ID: {res_id_b}")
    _wait()

    if res_id_b:
        _req(
            method="DELETE",
            path=f"/bookings/client/{res_id_b}/cancel",
            token=TOKEN_KATE,
            body=None,
            label=(
                "T-10 | kate cancels the second reservation\n"
                "  SQS      : CANCELLED — ignored by both report services\n"
                "  Expected : 200  |  reports UNCHANGED"
            ),
        )
    else:
        _skip("T-10", "no reservation ID from T-9")

    print(f"\n{'═' * 70}")
    print("  All tests completed.")
    print(f"  Main reservation  : {_context.get('main_res_id', 'N/A')}")
    print(f"  Cancel demo       : {_context.get('cancel_res_id', 'N/A')}")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()

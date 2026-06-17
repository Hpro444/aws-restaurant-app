"""Automated end-to-end tests for every API route, with DynamoDB verification.

Mirrors the fully automatic bootstrap of backend/test_sqs_endpoints.py:
validates AWS credentials (syndicate config first, env/SSO fallback), runs
the backend seeder (quick_seed) so the deployed tables hold fresh demo data,
resolves the API Gateway URL and the real DynamoDB table names at runtime,
then runs every suite in ``e2e.SUITE_ORDER`` — no pauses, no manual input.

Because this script sets ``E2E_ARTIFACTS_DIR``, the seeder writes ids.json
and tokens.json into automation-qa/ next to this file.  Each step records
the request sent, the response received, the HTTP assertion, and a
before/after DynamoDB check; the run finishes by writing a formatted
``test_output.pdf`` report next to this script.

Usage:
    python test_e2e_endpoints.py                 # seed + run everything
    python test_e2e_endpoints.py --skip-seed     # reuse existing seed data
    python test_e2e_endpoints.py --check-creds   # only validate AWS access
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import re
import sys
import traceback
from datetime import UTC, datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# ── Paths ─────────────────────────────────────────────────────────────────────

_HERE = pathlib.Path(__file__).parent
_BACKEND_DIR = _HERE.parent / "backend"
_TOKENS_FILE = _HERE / "tokens.json"
_IDS_FILE = _HERE / "ids.json"
_PDF_FILE = _HERE / "test_output.pdf"
_LOGS_DIR = _HERE / "logs"
_SYNDICATE_CONFIG = (
    _BACKEND_DIR / "restaurant-backend-app" / ".syndicate-config-dev" / "syndicate.yml"
)
_SYNDICATE_ALIASES = (
    _BACKEND_DIR
    / "restaurant-backend-app"
    / ".syndicate-config-dev"
    / "syndicate_aliases.yml"
)

# The seeder, token generator, and seeds package live in backend/.
sys.path.insert(0, str(_BACKEND_DIR))

from e2e import SUITE_ORDER  # noqa: E402
from e2e.config import AWS_REGION, STAGE, TRACKED_TABLE_ALIASES  # noqa: E402
from e2e.context import E2EContext  # noqa: E402
from e2e.report import generate_pdf  # noqa: E402

# ── ANSI colours ──────────────────────────────────────────────────────────────

_GREEN = "\033[92m"
_RED = "\033[91m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

DSEP = "═" * 70


# ── Run logging ───────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _TeeLogger:
    """Mirror everything written to stdout into a log file (ANSI stripped).

    The console keeps its colours; the log file gets plain text so failures
    can be inspected after the run without terminal escape noise.
    """

    def __init__(self, stream, log_file) -> None:
        """Wrap ``stream`` and duplicate writes into ``log_file``."""
        self._stream = stream
        self._log = log_file

    def write(self, text: str) -> None:
        """Write to the console and append the ANSI-stripped text to the log."""
        self._stream.write(text)
        self._log.write(_ANSI_RE.sub("", text))

    def flush(self) -> None:
        """Flush both sinks."""
        self._stream.flush()
        self._log.flush()


# ── Credential / resolution helpers (same approach as test_sqs_endpoints) ────


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


def _build_session() -> tuple[object, str] | None:
    """Return a validated (boto3 session, account id) pair, or None.

    Tries the syndicate config credentials first; when those are missing or
    expired, falls back to the environment / profile (e.g. SSO) credentials.
    """
    print("▶ Loading AWS credentials...")
    creds = _load_syndicate_credentials()
    if creds:
        candidate = boto3.session.Session(region_name=AWS_REGION, **creds)
        try:
            identity = candidate.client("sts").get_caller_identity()
            print("  ✓ Loaded from syndicate config")
            print(f"  ✓ Account: {identity['Account']}  |  {identity['Arn']}")
            return candidate, identity["Account"]
        except (ClientError, NoCredentialsError):
            print("  ⚠ Syndicate credentials expired — falling back to env/profile")

    candidate = boto3.session.Session(region_name=AWS_REGION)
    try:
        identity = candidate.client("sts").get_caller_identity()
        print("  ✓ Using environment / profile credentials")
        print(f"  ✓ Account: {identity['Account']}  |  {identity['Arn']}")
        return candidate, identity["Account"]
    except (ClientError, NoCredentialsError) as exc:
        print(f"{_RED}  ✗ No valid AWS credentials: {exc}{_RESET}")
        print("  Refresh syndicate temp credentials or run 'aws sso login'.")
        return None


def _resolve_base_url(session) -> str | None:
    """Resolve the API Gateway invoke URL from deployed REST APIs."""
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
                    f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{STAGE}"
                )
            position = resp.get("position")
            if not position:
                break
    except Exception as exc:
        print(f"  ⚠ API Gateway lookup failed: {exc}")

    return None


def _resolve_table(dyn_client, alias: str) -> str | None:
    """Return the real DynamoDB table name for a logical alias, or None."""
    prefix = suffix = ""
    if _SYNDICATE_CONFIG.exists():
        content = _SYNDICATE_CONFIG.read_text(encoding="utf-8")
        prefix = _extract_yml_value(content, "resources_prefix") or ""
        suffix = _extract_yml_value(content, "resources_suffix") or ""

    # Map alias to lookup name from syndicate_aliases.yml (e.g. waiter-report).
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
    for candidate in dict.fromkeys(candidates):
        try:
            dyn_client.describe_table(TableName=candidate)
            return candidate
        except ClientError:
            pass

    try:
        for name in dyn_client.list_tables().get("TableNames", []):
            if alias in name:
                return name
    except ClientError:
        pass

    return None


# ── Token + ID loading ────────────────────────────────────────────────────────


def _load_tokens() -> dict[str, str]:
    """Read access tokens from tokens.json keyed by email."""
    if not _TOKENS_FILE.exists():
        print(f"{_RED}  ERROR: tokens.json not found at {_TOKENS_FILE}{_RESET}")
        print("  Seeding should have produced it — check the seeder output above.")
        sys.exit(1)
    raw = json.loads(_TOKENS_FILE.read_text(encoding="utf-8"))
    return {email: data["access_token"] for email, data in raw.items()}


def _load_ids() -> dict:
    """Read seeded entity IDs from ids.json."""
    if not _IDS_FILE.exists():
        print(f"{_RED}  ERROR: ids.json not found at {_IDS_FILE}{_RESET}")
        print("  Seeding should have produced it — check the seeder output above.")
        sys.exit(1)
    return json.loads(_IDS_FILE.read_text(encoding="utf-8"))


# ── Main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """Bootstrap AWS access, seed, run every suite, and write the PDF report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-creds",
        action="store_true",
        help="Only validate AWS credentials and exit (used by run_e2e scripts).",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip quick_seed and reuse existing ids.json/tokens.json.",
    )
    args = parser.parse_args(argv)

    # Seeder + token generator write ids.json/tokens.json next to this script.
    os.environ["E2E_ARTIFACTS_DIR"] = str(_HERE)

    started_at = datetime.now(UTC)

    # Mirror all console output into logs/e2e_<timestamp>.log for debugging.
    # --check-creds is a lightweight probe used by the run scripts — no log.
    log_file = None
    original_stdout = sys.stdout
    if not args.check_creds:
        _LOGS_DIR.mkdir(exist_ok=True)
        log_path = _LOGS_DIR / f"e2e_{started_at.strftime('%Y%m%d_%H%M%S')}.log"
        log_file = log_path.open("w", encoding="utf-8")
        sys.stdout = _TeeLogger(original_stdout, log_file)
        print(f"▶ Run log: {log_path}")

    try:
        return _run(args, started_at)
    finally:
        sys.stdout = original_stdout
        if log_file is not None:
            log_file.close()


def _run(args, started_at) -> int:
    """Execute the e2e run (credentials, seed, suites, summary, PDF, JSON)."""
    print(f"\n{DSEP}")
    print("  FULL E2E ENDPOINT TESTS  (automated)")
    print(DSEP)

    # ── 0. Validate AWS credentials ────────────────────────────────────────
    built = _build_session()
    if built is None:
        return 1
    session, account = built
    if args.check_creds:
        print(f"{_GREEN}  ✓ Credentials are valid{_RESET}")
        return 0

    # ── 1. Seed the deployed environment (also refreshes Cognito tokens) ──
    if args.skip_seed:
        print("▶ Skipping seed (--skip-seed); refreshing Cognito tokens only...")
        try:
            import generate_tokens as _gt

            frozen = session.get_credentials().get_frozen_credentials()
            valid_creds = {
                "aws_access_key_id": frozen.access_key,
                "aws_secret_access_key": frozen.secret_key,
            }
            if frozen.token:
                valid_creds["aws_session_token"] = frozen.token
            _gt.generate_all({"aws_credentials": valid_creds})
            print("  ✓ Tokens refreshed")
        except Exception as exc:
            print(f"  ⚠ Token refresh failed (will use cached): {exc}")
    else:
        print("▶ Seeding the deployed environment (quick_seed)...")
        import quick_seed

        seed_rc = quick_seed.main()
        if seed_rc != 0:
            print(f"{_RED}  ✗ Seeding failed (exit {seed_rc}) — aborting.{_RESET}")
            return 1

    # ── 2. Load tokens and IDs produced by the seeder ──────────────────────
    tokens = _load_tokens()
    ids = _load_ids()

    # ── 3. Resolve the API Gateway URL ─────────────────────────────────────
    print("▶ Resolving API Gateway URL...")
    base_url = _resolve_base_url(session)
    if not base_url:
        print(f"{_RED}  ✗ Could not resolve API Gateway URL automatically{_RESET}")
        return 1
    print(f"  ✓ {base_url}")

    # ── 4. Resolve DynamoDB tables used for verification ──────────────────
    print("▶ Resolving DynamoDB table names...")
    dyn_client = session.client("dynamodb", region_name=AWS_REGION)
    dynamodb = session.resource("dynamodb", region_name=AWS_REGION)
    tables: dict[str, object] = {}
    for alias in TRACKED_TABLE_ALIASES:
        real_name = _resolve_table(dyn_client, alias)
        if real_name:
            tables[alias] = dynamodb.Table(real_name)
            print(f"  ✓ {alias:<18} → {real_name}")
        else:
            print(f"  ⚠ {alias:<18} → not found (DB checks on it will fail)")

    # ── 5. Run every suite in order ────────────────────────────────────────
    ctx = E2EContext(
        base_url=base_url,
        tokens=tokens,
        ids=ids,
        dynamodb=dynamodb,
        tables=tables,
    )

    for suite_name in SUITE_ORDER:
        print(f"\n{DSEP}")
        print(f"  SUITE: {suite_name.upper()}")
        print(DSEP)
        try:
            module = importlib.import_module(f"e2e.{suite_name}")
            module.run(ctx)
        except Exception:
            print(f"{_RED}  ✗ Suite '{suite_name}' crashed:{_RESET}")
            traceback.print_exc()

    # ── 6. Summary + PDF report ────────────────────────────────────────────
    finished_at = datetime.now(UTC)
    results = ctx.recorder.results
    passed = ctx.recorder.passed_count
    total = len(results)

    print(f"\n{DSEP}")
    print(f"  {_BOLD}TEST RESULTS{_RESET}")
    print(DSEP)
    for result in results:
        mark = f"{_GREEN}✓{_RESET}" if result.passed else f"{_RED}✗{_RESET}"
        suffix = (
            f"  {_DIM}{result.reason}{_RESET}"
            if result.reason and not result.passed
            else ""
        )
        print(f"  {mark}  {result.step:<8} {result.method:<7} {result.path}{suffix}")
    color = _GREEN if passed == total else _RED
    print(f"\n  {color}{_BOLD}{passed}/{total} passed{_RESET}")
    print(DSEP)

    meta = {
        "base_url": base_url,
        "account": account,
        "region": AWS_REGION,
        "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Machine-readable dump of every step (full request/response/DB checks)
    # so a failed run can be diffed and debugged without re-running anything.
    print("\n▶ Writing JSON results...")
    json_path = _LOGS_DIR / f"e2e_{started_at.strftime('%Y%m%d_%H%M%S')}_results.json"
    try:
        json_path.write_text(
            json.dumps(
                {
                    "meta": meta,
                    "passed": passed,
                    "total": total,
                    "steps": [r.model_dump() for r in results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  ✓ Results written to {json_path}")
    except Exception:
        print(f"{_RED}  ✗ JSON results dump failed:{_RESET}")
        traceback.print_exc()

    print("\n▶ Generating PDF report...")
    try:
        generate_pdf(ctx.recorder, meta, str(_PDF_FILE))
        print(f"  ✓ Report written to {_PDF_FILE}")
    except Exception:
        print(f"{_RED}  ✗ PDF generation failed:{_RESET}")
        traceback.print_exc()
        return 1

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

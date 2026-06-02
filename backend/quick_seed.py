#!/usr/bin/env python3
"""Quick seed script to populate AWS DynamoDB with demo restaurant data.

Run this AFTER 'syndicate deploy' to populate the deployed DynamoDB tables.

Usage:
    python quick_seed.py
"""

import importlib
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

import generate_tokens

# Add pyapp/src to path so seed modules can import domain models.
PYAPP_SRC = Path(__file__).parent / "restaurant-backend-app" / "pyapp" / "src"
sys.path.insert(0, str(PYAPP_SRC))

# Add the backend directory so the seeds package is importable.
sys.path.insert(0, str(Path(__file__).parent))

import seeds
from seeds.config import AWS_REGION, SLOT_SEED_DAYS_AHEAD
from seeds.utils import seed_id

SYNDICATE_CONFIG = (
    Path(__file__).parent
    / "restaurant-backend-app"
    / ".syndicate-config-dev"
    / "syndicate.yml"
)

SYNDICATE_ALIASES = (
    Path(__file__).parent
    / "restaurant-backend-app"
    / ".syndicate-config-dev"
    / "syndicate_aliases.yml"
)


def resolve_table_name(dynamodb_client, alias: str) -> str:
    """Resolve actual DynamoDB table name by trying deterministic candidates first."""
    content = (
        SYNDICATE_CONFIG.read_text(encoding="utf-8")
        if SYNDICATE_CONFIG.exists()
        else ""
    )
    resources_prefix = _extract_config_value(content, "resources_prefix") or ""
    resources_suffix = _extract_config_value(content, "resources_suffix") or ""

    candidates = [
        alias,
        f"{resources_prefix}{alias}{resources_suffix}",
    ]

    seen = set()
    candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

    for candidate in candidates:
        try:
            dynamodb_client.describe_table(TableName=candidate)
            print(f"  ✓ Resolved '{alias}' → {candidate}")
            return candidate
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code not in {
                "ResourceNotFoundException",
                "ValidationException",
                "AccessDeniedException",
            }:
                print(f"  ✗ Failed to describe table '{candidate}': {e}")

    # Last-resort path for environments where ListTables permission exists.
    try:
        response = dynamodb_client.list_tables()
        for table_name in response.get("TableNames", []):
            if alias in table_name:
                print(f"  ✓ Resolved '{alias}' → {table_name}")
                return table_name
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "AccessDeniedException":
            print(f"  ✗ Failed to list tables: {e}")

    print(f"  ✗ Could not find table containing '{alias}'")
    return None


def _extract_config_value(content: str, key: str) -> str | None:
    """Extract plain scalar value from simple YAML key-value line."""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", content, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return value or None


def _load_table_aliases() -> dict[str, str]:
    """Build alias→lookup mapping from all *_table entries in syndicate_aliases.yml."""
    aliases = {}
    for line in SYNDICATE_ALIASES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ": " not in line:
            continue
        key, value = line.split(": ", 1)
        key = key.strip()
        if not key.endswith("_table"):
            continue
        alias = key[: -len("_table")]
        aliases[alias] = value.strip().strip('"').strip("'")
    return aliases


def load_syndicate_credentials() -> dict | None:
    """Load AWS credentials from syndicate.yml if available."""
    if not SYNDICATE_CONFIG.exists():
        return None

    content = SYNDICATE_CONFIG.read_text(encoding="utf-8")

    # Prefer temp credentials first if present.
    access_key = _extract_config_value(content, "temp_aws_access_key_id")
    secret_key = _extract_config_value(content, "temp_aws_secret_access_key")
    session_token = _extract_config_value(content, "temp_aws_session_token")

    if not (access_key and secret_key and session_token):
        access_key = _extract_config_value(content, "aws_access_key_id")
        secret_key = _extract_config_value(content, "aws_secret_access_key")
        session_token = _extract_config_value(content, "aws_session_token")

    if access_key and secret_key and session_token:
        return {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "aws_session_token": session_token,
        }

    return None


def _wait_for_tables_active(
    dynamodb_client, table_names: list[str], timeout: int = 120
) -> None:
    """Block until every table in table_names has status ACTIVE.

    Polls every 5 seconds. Raises RuntimeError if timeout is exceeded.
    """
    deadline = time.monotonic() + timeout
    pending = set(table_names)
    while pending:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Tables still not ACTIVE after {timeout}s: {', '.join(pending)}"
            )
        still_creating = set()
        for name in pending:
            try:
                resp = dynamodb_client.describe_table(TableName=name)
                status = resp["Table"]["TableStatus"]
                if status != "ACTIVE":
                    still_creating.add(name)
            except ClientError:
                still_creating.add(name)
        if still_creating:
            print(
                f"  ⏳ Waiting for {len(still_creating)} table(s) to become ACTIVE "
                f"({', '.join(sorted(still_creating))})..."
            )
            time.sleep(5)
        pending = still_creating


def main():
    """Run seeding orchestration — imports and runs every module in seeds.SEED_ORDER."""
    print("\n" + "=" * 70)
    print("  RESTAURANT APP — AWS DYNAMODB SEEDER")
    print("=" * 70 + "\n")

    # Build session from environment first, then fallback to syndicate config.
    credentials = load_syndicate_credentials()
    if credentials:
        print("▶ Loaded AWS credentials from syndicate config")
        session = boto3.session.Session(region_name=AWS_REGION, **credentials)
    else:
        print("▶ Using AWS credentials from environment/profile")
        session = boto3.session.Session(region_name=AWS_REGION)

    # Verify AWS access.
    print("▶ Verifying AWS credentials...")
    try:
        sts = session.client("sts", region_name=AWS_REGION)
        identity = sts.get_caller_identity()
        print(f"  ✓ AWS Account: {identity['Account']}")
        print(f"  ✓ Caller ARN: {identity['Arn']}\n")
    except (ClientError, NoCredentialsError) as e:
        print(f"  ✗ AWS credentials invalid: {e}")
        print("     Run 'aws sso login' or check your credentials.\n")
        return 1

    # Resolve actual DynamoDB table names (handles syndicate prefix/suffix).
    print("▶ Resolving DynamoDB table names (region: eu-west-3)...")
    dynamodb_client = session.client("dynamodb", region_name=AWS_REGION)
    dynamodb = session.resource("dynamodb", region_name=AWS_REGION)
    resolved_tables = {}
    missing = []
    for alias, lookup_name in _load_table_aliases().items():
        real_name = resolve_table_name(dynamodb_client, lookup_name)
        if real_name:
            resolved_tables[alias] = real_name
        else:
            missing.append(alias)

    if missing:
        print(
            f"\n  ⚠ Tables not found — their seeds will be skipped: {', '.join(missing)}\n"
        )

    # Wait for all resolved tables to be ACTIVE before writing.
    if resolved_tables:
        print("▶ Waiting for all tables to be ACTIVE...")
        try:
            _wait_for_tables_active(dynamodb_client, list(resolved_tables.values()))
            print("  ✓ All tables ACTIVE\n")
        except RuntimeError as e:
            print(f"  ✗ {e}\n")
            return 1

    # Extract prefix/suffix so seeders (e.g. Cognito) can build exact resource names.
    syndicate_content = (
        SYNDICATE_CONFIG.read_text(encoding="utf-8")
        if SYNDICATE_CONFIG.exists()
        else ""
    )
    resources_prefix = (
        _extract_config_value(syndicate_content, "resources_prefix") or ""
    )
    resources_suffix = (
        _extract_config_value(syndicate_content, "resources_suffix") or ""
    )

    # Import and run each seed module in order.
    print("▶ Seeding demo data...")
    context: dict = {
        "aws_credentials": credentials or {},
        "aws_region": AWS_REGION,
        "resources_prefix": resources_prefix,
        "resources_suffix": resources_suffix,
        "slot_seed_days_ahead": SLOT_SEED_DAYS_AHEAD,
    }
    current_module = None
    try:
        for module_name in seeds.SEED_ORDER:
            current_module = module_name
            module = importlib.import_module(f"seeds.{module_name}")
            try:
                module.seed(dynamodb, resolved_tables, context)
            except KeyError as e:
                print(f"  ⚠ Skipping {module_name}: table {e} not available")
    except ClientError as e:
        print(f"\n  ✗ Seeding failed in '{current_module}' (AWS ClientError): {e}")
        print(
            "     Verify IAM permissions for dynamodb:PutItem/BatchWriteItem and table names.\n"
        )
        return 1
    except Exception as e:
        print(f"\n  ✗ Seeding failed in '{current_module}': {e}\n")
        import traceback

        traceback.print_exc()
        return 1

    # Summary.
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_seeded_date = (
        datetime.now(timezone.utc) + timedelta(days=SLOT_SEED_DAYS_AHEAD)
    ).strftime("%Y-%m-%d")
    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")
    cognito_subs = context.get("cognito_subs", {})
    lea_id = cognito_subs.get("lea@example.com", str(seed_id("waiter", "lea")))
    max_id = cognito_subs.get("max@example.com", str(seed_id("waiter", "max")))
    nina_id = cognito_subs.get("nina@example.com", str(seed_id("waiter", "nina")))

    print("\n" + "=" * 70)
    print("  ✅ SEEDING COMPLETE")
    print("=" * 70)
    print("\n📊 View seeded data in AWS Console:")
    print("   https://console.aws.amazon.com/dynamodb/home?region=eu-west-3#tables:")
    print("\n📝 Seeded IDs for testing:")
    print(f"   - Location (Downtown):                  {downtown_id}")
    print(f"   - Location (Airport):                   {airport_id}")
    print(f"   - Location (Old Town):                  {old_town_id}")
    print(f"   - Waiter (Lea)   lea@example.com:       {lea_id}")
    print(f"   - Waiter (Max)   max@example.com:       {max_id}")
    print(f"   - Waiter (Nina)  nina@example.com:      {nina_id}")
    print(
        f"   - Customer (Alice)  alice@example.com:  {cognito_subs.get('alice@example.com', str(seed_id('customer', 'alice')))}"
    )
    print(
        f"   - Customer (Bob)    bob@example.com:    {cognito_subs.get('bob@example.com', str(seed_id('customer', 'bob')))}"
    )
    print(
        f"   - Customer (Carol)  carol@example.com:  {cognito_subs.get('carol@example.com', str(seed_id('customer', 'carol')))}"
    )
    print("\n🔑 Demo credentials (all seeded users): Password123@")
    print(f"   - Slots seeded for date range: {today_date} → {last_seeded_date}")
    print()
    print("🧪 Ready-to-use API test URLs (replace BASE_URL with your API Gateway URL):")
    print(
        f"   GET /api/bookings/tables?location_id={downtown_id}&date={today_date}&guests_number=2"
    )
    print(
        f"   GET /api/bookings/tables?location_id={airport_id}&date={today_date}&guests_number=2"
    )
    print(
        f"   GET /api/bookings/tables?location_id={old_town_id}&date={last_seeded_date}&guests_number=2"
    )
    print()

    print("▶ Generating Cognito tokens for seeded users...")
    try:
        generate_tokens.generate_all(context)
    except Exception as e:
        print(f"  ⚠ Token generation failed (non-fatal): {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

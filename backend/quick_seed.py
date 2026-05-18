#!/usr/bin/env python3
"""Quick seed script to populate AWS DynamoDB with demo restaurant data.

Run this AFTER 'syndicate deploy' to populate the deployed DynamoDB tables.

Usage:
    python quick_seed.py
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add pyapp/src to path for domain imports
PYAPP_SRC = Path(__file__).parent / "restaurant-backend-app" / "pyapp" / "src"
sys.path.insert(0, str(PYAPP_SRC))

# ruff: noqa: E402
from domain.location import Location  # type: ignore[import-not-found]
from domain.reservation import (
    Reservation,  # type: ignore[import-not-found]
)
from domain.slot import Slot  # type: ignore[import-not-found]
from domain.table import Table  # type: ignore[import-not-found]
from enums.reservation_status import (
    ReservationStatus,  # type: ignore[import-not-found]
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

AWS_REGION = "eu-west-3"
NAMESPACE = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

TABLE_ALIASES = {
    "locations": "locations",
    "reservations": "reservations",
    "tables": "tables",
    "slots": "slots",
}

SYNDICATE_CONFIG = (
    Path(__file__).parent
    / "restaurant-backend-app"
    / ".syndicate-config-dev"
    / "syndicate.yml"
)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────


def seed_id(entity_type: str, natural_key: str) -> UUID:
    """Generate deterministic UUID5 for reproducible seeding."""
    return uuid5(NAMESPACE, f"{entity_type}:{natural_key}")


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


# ─────────────────────────────────────────────────────────────────────────────
# Seeders
# ─────────────────────────────────────────────────────────────────────────────


def seed_locations(dynamodb, table_name: str) -> dict:
    """Seed 2 restaurant locations."""
    table = dynamodb.Table(table_name)

    locations = [
        Location(
            id=seed_id("location", "downtown"),
            name="Downtown",
            address="123 Main Street",
            description="Central city location near the main square.",
            image_url="https://images.example.com/locations/downtown.jpg",
            open_time="10:00",
            close_time="22:00",
        ),
        Location(
            id=seed_id("location", "airport"),
            name="Airport Terminal",
            address="456 Terminal Boulevard",
            description="Fast-service location inside the international terminal.",
            image_url="https://images.example.com/locations/airport.jpg",
            open_time="06:00",
            close_time="23:00",
        ),
    ]

    with table.batch_writer() as batch:
        for loc in locations:
            batch.put_item(Item=loc.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(locations)} locations")
    return {loc.id: loc for loc in locations}


def seed_tables(dynamodb, table_name: str, locations: dict):
    """Seed 5 tables per location."""
    table = dynamodb.Table(table_name)

    tables_list = []
    for location_key, location_obj in locations.items():
        for table_num in range(1, 6):
            t = Table(
                id=seed_id("table", f"{location_key}:{table_num}"),
                table_number=table_num,
                # capacity=10,
                capacity=10 if table_num % 2 == 0 else 5,
                location_id=location_obj.id,
            )
            tables_list.append(t)

    with table.batch_writer() as batch:
        for t in tables_list:
            batch.put_item(Item=t.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(tables_list)} tables")
    return tables_list


def seed_slots(dynamodb, table_name: str, tables_list: list, locations: dict):
    """Seed slots dynamically based on restaurant open and close times."""
    table = dynamodb.Table(table_name)

    slots_list = []

    for table_obj in tables_list:
        # Fetch the associated location's open and close times using location_id (UUID)
        location = locations.get(table_obj.location_id)
        if not location:
            print(f"  ! Skipping table {table_obj.id}: location not found")
            continue

        # Open and close times are already time objects from Location domain
        open_time = location.open_time
        close_time = location.close_time

        # Generate slots dynamically for tomorrow
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        tomorrow_date = tomorrow.date()
        current_time = datetime.combine(tomorrow_date, open_time, tzinfo=timezone.utc)
        end_of_day = datetime.combine(tomorrow_date, close_time, tzinfo=timezone.utc)

        while current_time + timedelta(minutes=90) <= end_of_day:
            start = current_time
            end = start + timedelta(minutes=90)

            s = Slot(
                id=seed_id("slot", f"{table_obj.id}:{start.hour}:{start.minute}"),
                table_id=table_obj.id,
                start_time=start,
                end_time=end,
                date=start,
            )
            slots_list.append(s)

            # Increment time by slot duration + break
            current_time = end + timedelta(minutes=15)

    with table.batch_writer() as batch:
        for s in slots_list:
            batch.put_item(Item=s.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(slots_list)} slots dynamically based on restaurant hours")
    return slots_list


def seed_reservations(dynamodb, table_name: str, slots_list: list[Slot]):
    """Seed a few mock reservations for availability testing.

    Creates three reservations on tomorrow's slots:
    - 2 active reservations (RESERVED, IN_PROGRESS) that block slots.
    - 1 CANCELLED reservation that should not block a slot.

    """
    table = dynamodb.Table(table_name)

    if len(slots_list) < 15:
        print("  ! Skipping reservations seed: not enough slots generated")
        return []

    # With 7 slots per table and deterministic slot order, these are first slots
    # of table #1, #2 and #3 respectively.
    chosen_slots = [slots_list[0], slots_list[7], slots_list[14]]
    created_at = datetime.now(timezone.utc)

    reservations = [
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[0].id}:reserved"),
            customer_id=seed_id("customer", "alice"),
            waiter_id=seed_id("waiter", "lea"),
            created_at=created_at,
            slot=chosen_slots[0].id,
            status=ReservationStatus.RESERVED,
            number_of_guests=4,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[1].id}:in-progress"),
            customer_id=seed_id("customer", "bob"),
            waiter_id=seed_id("waiter", "max"),
            created_at=created_at,
            slot=chosen_slots[1].id,
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[2].id}:cancelled"),
            customer_id=seed_id("customer", "carol"),
            waiter_id=None,
            created_at=created_at,
            slot=chosen_slots[2].id,
            status=ReservationStatus.CANCELLED,
            number_of_guests=3,
        ),
    ]

    with table.batch_writer() as batch:
        for reservation in reservations:
            batch.put_item(Item=reservation.model_dump(mode="json"))

    print(
        "  ✓ Seeded "
        f"{len(reservations)} reservations (2 active, 1 cancelled for testing)"
    )
    return reservations


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    """Run seeding orchestration."""
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

    # Verify AWS access
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

    # Initialize DynamoDB and use known table names from aliases.
    print("▶ Connecting to DynamoDB (region: eu-west-3)...")
    dynamodb = session.resource("dynamodb", region_name=AWS_REGION)
    resolved_tables = TABLE_ALIASES.copy()
    for alias_name, table_name in resolved_tables.items():
        print(f"  ✓ Using table for {alias_name}: {table_name}")

    # Seed data
    print("\n▶ Seeding demo data...")
    try:
        locations = seed_locations(dynamodb, resolved_tables["locations"])
        tables_list = seed_tables(dynamodb, resolved_tables["tables"], locations)
        slots_list = seed_slots(
            dynamodb, resolved_tables["slots"], tables_list, locations
        )
        seed_reservations(dynamodb, resolved_tables["reservations"], slots_list)
    except ClientError as e:
        print(f"\n  ✗ Seeding failed (AWS ClientError): {e}")
        print(
            "     Verify IAM permissions for dynamodb:PutItem/BatchWriteItem and table names.\n"
        )
        return 1
    except Exception as e:
        print(f"\n  ✗ Seeding failed: {e}\n")
        import traceback

        traceback.print_exc()
        return 1

    # Summary
    tomorrow_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")

    print("\n" + "=" * 70)
    print("  ✅ SEEDING COMPLETE")
    print("=" * 70)
    print("\n📊 View seeded data in AWS Console:")
    print("   https://console.aws.amazon.com/dynamodb/home?region=eu-west-3#tables:")
    print("\n📝 Seeded IDs for testing:")
    print(f"   - Location (Downtown): {downtown_id}")
    print(f"   - Location (Airport):  {airport_id}")
    print(f"   - Slots seeded for date: {tomorrow_date}")
    print()
    print("🧪 Ready-to-use API test URLs (replace BASE_URL with your API Gateway URL):")
    print(
        f"   GET /api/bookings/tables?location_id={downtown_id}&date={tomorrow_date}&guests_number=2"
    )
    print(
        f"   GET /api/bookings/tables?location_id={airport_id}&date={tomorrow_date}&guests_number=2"
    )
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

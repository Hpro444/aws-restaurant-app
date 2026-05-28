"""Seed module for table time slots."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError
from domain.slot import Slot  # type: ignore[import-not-found]
from tqdm import tqdm

from seeds.config import (
    DYNAMO_RETRY_CONFIG,
    SLOT_BREAK_MINUTES,
    SLOT_DURATION_MINUTES,
    THREAD_WORKERS,
)
from seeds.utils import seed_id


def _generate_day_slots(day_offset: int, tables_list: list, locations: dict) -> list:
    """Generate Slot objects for one calendar day (no I/O)."""
    today_date = datetime.now(timezone.utc).date()
    target_date = today_date + timedelta(days=day_offset)

    day_slots = []
    for table_obj in tables_list:
        location = locations.get(table_obj.location_id)
        if not location:
            continue

        current_time = datetime.combine(
            target_date, location.open_time, tzinfo=timezone.utc
        )
        end_of_day = datetime.combine(
            target_date, location.close_time, tzinfo=timezone.utc
        )

        while current_time + timedelta(minutes=SLOT_DURATION_MINUTES) <= end_of_day:
            start = current_time
            end = start + timedelta(minutes=SLOT_DURATION_MINUTES)
            day_slots.append(
                Slot(
                    id=seed_id(
                        "slot",
                        f"{table_obj.id}:{target_date.isoformat()}:{start.hour}:{start.minute}",
                    ),
                    table_id=table_obj.id,
                    start_time=start,
                    end_time=end,
                    date=start,
                )
            )
            current_time = end + timedelta(minutes=SLOT_BREAK_MINUTES)

    return day_slots


def _seed_day(
    day_offset: int,
    tables_list: list,
    locations: dict,
    credentials: dict,
    aws_region: str,
    table_name: str,
    pbar: tqdm,
) -> list:
    """Seed slots for one calendar day using a dedicated DynamoDB connection.

    Opens a fresh connection, writes all slots for the day, then closes it.
    On any ClientError, closes the bad connection and reopens a new one before retrying.
    """
    day_slots = _generate_day_slots(day_offset, tables_list, locations)

    session = boto3.session.Session(region_name=aws_region, **credentials)
    dyn_resource = session.resource(
        "dynamodb", region_name=aws_region, config=DYNAMO_RETRY_CONFIG
    )
    dyn_table = dyn_resource.Table(table_name)

    while True:
        try:
            with dyn_table.batch_writer() as batch:
                for s in day_slots:
                    batch.put_item(Item=s.model_dump(mode="json"))
            break
        except ClientError:
            dyn_resource.meta.client.close()
            session = boto3.session.Session(region_name=aws_region, **credentials)
            dyn_resource = session.resource(
                "dynamodb", region_name=aws_region, config=DYNAMO_RETRY_CONFIG
            )
            dyn_table = dyn_resource.Table(table_name)

    dyn_resource.meta.client.close()
    pbar.update(1)
    return day_slots


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 90-minute slots from today through today + SLOT_SEED_DAYS_AHEAD.

    Uses a ThreadPoolExecutor with 7 workers, one worker per day.
    Each worker opens its own DynamoDB connection, writes the day's slots,
    then closes it. On error the connection is replaced before retrying.
    Requires context['tables'], context['locations'],
    context['aws_credentials'], and context['aws_region'].
    """
    table_name = tables["slots"]
    tables_list = context["tables"]
    locations = context["locations"]
    credentials = context.get("aws_credentials", {})
    aws_region = context.get("aws_region", "eu-west-3")
    slot_seed_days_ahead = context["slot_seed_days_ahead"]

    day_offsets = list(range(slot_seed_days_ahead + 1))
    all_slots: list = []

    with tqdm(total=len(day_offsets), desc="  Seeding slots", unit="day") as pbar:
        with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as executor:
            futures = [
                executor.submit(
                    _seed_day,
                    offset,
                    tables_list,
                    locations,
                    credentials,
                    aws_region,
                    table_name,
                    pbar,
                )
                for offset in day_offsets
            ]
            for future in as_completed(futures):
                all_slots.extend(future.result())

    print(
        f"  ✓ Seeded {len(all_slots)} slots dynamically based on restaurant hours "
        f"(today + {slot_seed_days_ahead} days)"
    )
    context["slots"] = all_slots

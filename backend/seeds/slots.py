"""Seed module for table time slots."""

from datetime import datetime, timedelta, timezone

from domain.slot import Slot  # type: ignore[import-not-found]
from tqdm import tqdm

from seeds.utils import seed_id

SLOT_DURATION_MINUTES = 90
SLOT_BREAK_MINUTES = 15
SLOT_SEED_DAYS_AHEAD = 7


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 90-minute slots from today through today + SLOT_SEED_DAYS_AHEAD.

    Requires context['tables'] and context['locations'].
    """
    table = dynamodb.Table(tables["slots"])
    tables_list = context["tables"]
    locations = context["locations"]

    slots_list = []

    for table_obj in tables_list:
        location = locations.get(table_obj.location_id)
        if not location:
            print(f"  ! Skipping table {table_obj.id}: location not found")
            continue

        open_time = location.open_time
        close_time = location.close_time

        today_date = datetime.now(timezone.utc).date()

        for day_offset in range(SLOT_SEED_DAYS_AHEAD + 1):
            target_date = today_date + timedelta(days=day_offset)
            current_time = datetime.combine(target_date, open_time, tzinfo=timezone.utc)
            end_of_day = datetime.combine(target_date, close_time, tzinfo=timezone.utc)

            while current_time + timedelta(minutes=SLOT_DURATION_MINUTES) <= end_of_day:
                start = current_time
                end = start + timedelta(minutes=SLOT_DURATION_MINUTES)

                s = Slot(
                    id=seed_id(
                        "slot",
                        (
                            f"{table_obj.id}:"
                            f"{target_date.isoformat()}:"
                            f"{start.hour}:{start.minute}"
                        ),
                    ),
                    table_id=table_obj.id,
                    start_time=start,
                    end_time=end,
                    date=start,
                )
                slots_list.append(s)

                current_time = end + timedelta(minutes=SLOT_BREAK_MINUTES)

    with table.batch_writer() as batch:
        for s in tqdm(slots_list, desc="  Writing slots", unit="slot"):
            batch.put_item(Item=s.model_dump(mode="json"))

    print(
        "  ✓ Seeded "
        f"{len(slots_list)} slots dynamically based on restaurant hours "
        f"(today + {SLOT_SEED_DAYS_AHEAD} days)"
    )
    context["slots"] = slots_list

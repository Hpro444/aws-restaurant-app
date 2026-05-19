"""Seed module for table time slots."""

from datetime import datetime, timedelta, timezone

from domain.slot import Slot  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 90-minute slots for tomorrow based on each location's opening hours.

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

            current_time = end + timedelta(minutes=15)

    with table.batch_writer() as batch:
        for s in slots_list:
            batch.put_item(Item=s.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(slots_list)} slots dynamically based on restaurant hours")
    context["slots"] = slots_list

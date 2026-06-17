"""Seed module for waiter shifts."""

from datetime import datetime, timezone

from domain.shift import Shift  # type: ignore[import-not-found]

from seeds.utils import seed_id

_SHIFT_WAITERS_BY_LOCATION = {
    "downtown": {
        "first": ("lea@example.com", "charlie@example.com"),
        "second": ("olivia@example.com", "ethan@example.com"),
    },
    "airport": {
        "first": ("max@example.com", "sofia@example.com"),
        "second": ("liam@example.com", "mia@example.com"),
    },
    "old-town": {
        "first": ("nina@example.com", "noah@example.com"),
        "second": ("ava@example.com", "luka@example.com"),
    },
}

_LOCATION_KEYS = {
    "downtown": seed_id("location", "downtown"),
    "airport": seed_id("location", "airport"),
    "old-town": seed_id("location", "old-town"),
}


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed two shifts per location for today's slot halves.

    Each shift stores:
    - location_id
    - waiter_ids (2 waiters)
    - slot_ids (first or second half of location slots for one day)
    """
    table = dynamodb.Table(tables["shifts"])
    waiters = context["waiters"]
    tables_list = context["tables"]
    slots_list = context["slots"]

    today = datetime.now(timezone.utc).date()

    tables_by_location: dict = {}
    for table_obj in tables_list:
        tables_by_location.setdefault(table_obj.location_id, []).append(table_obj)

    slots_by_location: dict = {}
    for slot in slots_list:
        if slot.start_time.date() != today:
            continue

        table_match = next((t for t in tables_list if t.id == slot.table_id), None)
        if table_match is None:
            continue
        slots_by_location.setdefault(table_match.location_id, []).append(slot)

    shifts: list[Shift] = []
    for location_key, location_id in _LOCATION_KEYS.items():
        location_slots = sorted(
            slots_by_location.get(location_id, []),
            key=lambda slot: (slot.start_time, str(slot.table_id)),
        )
        if not location_slots:
            continue

        first_table = min(
            tables_by_location[location_id],
            key=lambda table_obj: table_obj.table_number,
        )
        first_table_times = [
            slot.start_time
            for slot in location_slots
            if slot.table_id == first_table.id
        ]

        if len(first_table_times) % 2 != 0:
            raise ValueError(f"Odd slot count for location {location_id}")

        split_index = len(first_table_times) // 2
        first_shift_times = set(first_table_times[:split_index])
        second_shift_times = set(first_table_times[split_index:])

        first_waiter_ids = [
            waiters[email].id
            for email in _SHIFT_WAITERS_BY_LOCATION[location_key]["first"]
        ]
        second_waiter_ids = [
            waiters[email].id
            for email in _SHIFT_WAITERS_BY_LOCATION[location_key]["second"]
        ]

        first_shift_slot_ids = [
            slot.id for slot in location_slots if slot.start_time in first_shift_times
        ]
        second_shift_slot_ids = [
            slot.id for slot in location_slots if slot.start_time in second_shift_times
        ]

        shifts.extend(
            [
                Shift(
                    id=seed_id("shift", f"{location_key}:first:{today.isoformat()}"),
                    location_id=location_id,
                    waiter_ids=first_waiter_ids,
                    slot_ids=first_shift_slot_ids,
                ),
                Shift(
                    id=seed_id("shift", f"{location_key}:second:{today.isoformat()}"),
                    location_id=location_id,
                    waiter_ids=second_waiter_ids,
                    slot_ids=second_shift_slot_ids,
                ),
            ]
        )

    with table.batch_writer() as batch:
        for shift in shifts:
            batch.put_item(Item=shift.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(shifts)} shifts")
    context["shifts"] = shifts

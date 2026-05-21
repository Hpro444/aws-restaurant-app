"""Seed module for waiter shifts."""

from domain.shift import Shift  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 1 shift per waiter covering the first 3 slots of their location's first table.

    Requires context['waiters'], context['tables'], and context['slots'].
    """
    table = dynamodb.Table(tables["shifts"])
    waiters = context["waiters"]
    tables_list = context["tables"]
    slots_list = context["slots"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    def first_slots_for_location(location_id, count: int = 3) -> list:
        """Return the first ``count`` slots belonging to the first table of the given location."""
        location_tables = [t for t in tables_list if t.location_id == location_id]
        if not location_tables:
            return []
        first_table = location_tables[0]
        table_slots = [s for s in slots_list if s.table_id == first_table.id]
        return table_slots[:count]

    lea_id = seed_id("waiter", "lea")
    max_id = seed_id("waiter", "max")
    nina_id = seed_id("waiter", "nina")

    shifts = [
        Shift(
            id=seed_id("shift", "lea:tomorrow"),
            waiter_id=waiters[lea_id].id,
            slots=[s.id for s in first_slots_for_location(downtown_id)],
        ),
        Shift(
            id=seed_id("shift", "max:tomorrow"),
            waiter_id=waiters[max_id].id,
            slots=[s.id for s in first_slots_for_location(airport_id)],
        ),
        Shift(
            id=seed_id("shift", "nina:tomorrow"),
            waiter_id=waiters[nina_id].id,
            slots=[s.id for s in first_slots_for_location(old_town_id)],
        ),
    ]

    with table.batch_writer() as batch:
        for shift in shifts:
            batch.put_item(Item=shift.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(shifts)} shifts")

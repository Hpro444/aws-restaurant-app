"""Seed module for the waiter-email allow-list."""

from domain.waiter_emails import WaiterEmail  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed waiter email allow-list with 4 waiters per location.

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["waiter_emails"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    entries = [
        WaiterEmail(
            email="lea@example.com",
            location_id=locations[downtown_id].id,
        ),
        WaiterEmail(
            email="charlie@example.com",
            location_id=locations[downtown_id].id,
        ),
        WaiterEmail(
            email="olivia@example.com",
            location_id=locations[downtown_id].id,
        ),
        WaiterEmail(
            email="ethan@example.com",
            location_id=locations[downtown_id].id,
        ),
        WaiterEmail(
            email="max@example.com",
            location_id=locations[airport_id].id,
        ),
        WaiterEmail(
            email="sofia@example.com",
            location_id=locations[airport_id].id,
        ),
        WaiterEmail(
            email="liam@example.com",
            location_id=locations[airport_id].id,
        ),
        WaiterEmail(
            email="mia@example.com",
            location_id=locations[airport_id].id,
        ),
        WaiterEmail(
            email="nina@example.com",
            location_id=locations[old_town_id].id,
        ),
        WaiterEmail(
            email="noah@example.com",
            location_id=locations[old_town_id].id,
        ),
        WaiterEmail(
            email="ava@example.com",
            location_id=locations[old_town_id].id,
        ),
        WaiterEmail(
            email="luka@example.com",
            location_id=locations[old_town_id].id,
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} waiter email entries")

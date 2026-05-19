"""Seed module for the waiter-email allow-list."""

from domain.waiter_emails import WaiterEmail  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed waiter email allow-list so lea and max can register as waiters.

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["waiter_emails"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")

    entries = [
        WaiterEmail(
            email="lea@example.com",
            location_id=locations[downtown_id].id,
        ),
        WaiterEmail(
            email="max@example.com",
            location_id=locations[airport_id].id,
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} waiter email entries")

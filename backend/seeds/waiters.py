"""Seed module for waiter profiles."""

from domain.user import Waiter  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 2 demo waiters and write them to context['waiters'].

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["waiters"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")

    waiters = [
        Waiter(
            id=seed_id("waiter", "lea"),
            fname="Lea",
            lname="Martinez",
            email="lea@example.com",
            image_url="https://images.example.com/waiters/lea.jpg",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=seed_id("waiter", "max"),
            fname="Max",
            lname="Fischer",
            email="max@example.com",
            image_url="https://images.example.com/waiters/max.jpg",
            location_id=locations[airport_id].id,
        ),
    ]

    with table.batch_writer() as batch:
        for waiter in waiters:
            batch.put_item(Item=waiter.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(waiters)} waiters")
    context["waiters"] = {w.id: w for w in waiters}

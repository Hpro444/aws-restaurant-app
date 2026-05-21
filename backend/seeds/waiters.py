"""Seed module for waiter profiles."""

from domain.user import Waiter  # type: ignore[import-not-found]

from seeds.utils import seed_id

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed demo waiters and write them to context['waiters'].

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["waiters"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    waiters = [
        Waiter(
            id=seed_id("waiter", "lea"),
            fname="Lea",
            lname="Martinez",
            email="lea@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=seed_id("waiter", "max"),
            fname="Max",
            lname="Fischer",
            email="max@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
            location_id=locations[airport_id].id,
        ),
        Waiter(
            id=seed_id("waiter", "nina"),
            fname="Nina",
            lname="Beridze",
            email="nina@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
            location_id=locations[old_town_id].id,
        ),
    ]

    with table.batch_writer() as batch:
        for waiter in waiters:
            batch.put_item(Item=waiter.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(waiters)} waiters")
    context["waiters"] = {w.id: w for w in waiters}

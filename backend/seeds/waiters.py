"""Seed module for waiter profiles."""

from uuid import UUID

from domain.user import Waiter  # type: ignore[import-not-found]

from seeds.utils import seed_id

_S3 = "https://epam-restaurantapp-dev-eu-west-3-frontend.s3.eu-west-3.amazonaws.com/images"


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed demo waiters using Cognito subs as DynamoDB IDs.

    Requires ``context["cognito_subs"]`` populated by the cognito_users seeder
    and ``context["locations"]`` populated by the locations seeder.
    Writes ``context["waiters"]`` keyed by email for downstream seeders.
    """
    table = dynamodb.Table(tables["waiters"])
    locations = context["locations"]
    subs = context["cognito_subs"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    waiters = [
        Waiter(
            id=UUID(subs["lea@example.com"]),
            fname="Lea",
            lname="Martinez",
            email="lea@example.com",
            image_url=f"{_S3}/user_avatar_1.png",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=UUID(subs["charlie@example.com"]),
            fname="Charlie",
            lname="Petrov",
            email="charlie@example.com",
            image_url=f"{_S3}/user_avatar_4.png",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=UUID(subs["olivia@example.com"]),
            fname="Olivia",
            lname="Mchedlishvili",
            email="olivia@example.com",
            image_url=f"{_S3}/user_avatar_5.png",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=UUID(subs["ethan@example.com"]),
            fname="Ethan",
            lname="Kapanadze",
            email="ethan@example.com",
            image_url=f"{_S3}/user_avatar_6.png",
            location_id=locations[downtown_id].id,
        ),
        Waiter(
            id=UUID(subs["max@example.com"]),
            fname="Max",
            lname="Fischer",
            email="max@example.com",
            image_url=f"{_S3}/user_avatar_2.png",
            location_id=locations[airport_id].id,
        ),
        Waiter(
            id=UUID(subs["sofia@example.com"]),
            fname="Sofia",
            lname="Abashidze",
            email="sofia@example.com",
            image_url=f"{_S3}/user_avatar_7.png",
            location_id=locations[airport_id].id,
        ),
        Waiter(
            id=UUID(subs["liam@example.com"]),
            fname="Liam",
            lname="Gelashvili",
            email="liam@example.com",
            image_url=f"{_S3}/user_avatar_8.png",
            location_id=locations[airport_id].id,
        ),
        Waiter(
            id=UUID(subs["mia@example.com"]),
            fname="Mia",
            lname="Gogoladze",
            email="mia@example.com",
            image_url=f"{_S3}/user_avatar_9.png",
            location_id=locations[airport_id].id,
        ),
        Waiter(
            id=UUID(subs["nina@example.com"]),
            fname="Nina",
            lname="Beridze",
            email="nina@example.com",
            image_url=f"{_S3}/user_avatar_3.png",
            location_id=locations[old_town_id].id,
        ),
        Waiter(
            id=UUID(subs["noah@example.com"]),
            fname="Noah",
            lname="Chelidze",
            email="noah@example.com",
            image_url=f"{_S3}/user_avatar_10.png",
            location_id=locations[old_town_id].id,
        ),
        Waiter(
            id=UUID(subs["ava@example.com"]),
            fname="Ava",
            lname="Dolidze",
            email="ava@example.com",
            image_url=f"{_S3}/user_avatar_11.png",
            location_id=locations[old_town_id].id,
        ),
        Waiter(
            id=UUID(subs["luka@example.com"]),
            fname="Luka",
            lname="Maisuradze",
            email="luka@example.com",
            image_url=f"{_S3}/user_avatar_12.png",
            location_id=locations[old_town_id].id,
        ),
    ]

    with table.batch_writer() as batch:
        for waiter in waiters:
            batch.put_item(Item=waiter.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(waiters)} waiters")
    context["waiters"] = {w.email: w for w in waiters}

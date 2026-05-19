"""Seed module for restaurant locations."""

from domain.location import Location  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 2 restaurant locations and write them to context['locations']."""
    table = dynamodb.Table(tables["locations"])

    locations = [
        Location(
            id=seed_id("location", "downtown"),
            name="Downtown",
            address="123 Main Street",
            description="Central city location near the main square.",
            image_url="https://images.example.com/locations/downtown.jpg",
            open_time="10:00",
            close_time="22:00",
        ),
        Location(
            id=seed_id("location", "airport"),
            name="Airport Terminal",
            address="456 Terminal Boulevard",
            description="Fast-service location inside the international terminal.",
            image_url="https://images.example.com/locations/airport.jpg",
            open_time="06:00",
            close_time="23:00",
        ),
    ]

    with table.batch_writer() as batch:
        for loc in locations:
            batch.put_item(Item=loc.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(locations)} locations")
    context["locations"] = {loc.id: loc for loc in locations}

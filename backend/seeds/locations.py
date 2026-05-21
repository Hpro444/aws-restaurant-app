"""Seed module for restaurant locations."""

from domain.location import Location  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 2 restaurant locations and write them to context['locations']."""
    table = dynamodb.Table(tables["locations"])

    locations = [
        Location(
            id=seed_id("location", "downtown"),
            name="48 Rustaveli Avenue, Tbilisi",
            address="48 Rustaveli Avenue, Tbilisi",
            description="Central city location near the main square.",
            image_url="http://epam-restaurantapp-dev-eu-west-3-frontend.s3-website.eu-west-3.amazonaws.com/location_img.jpg",
            open_time="10:00",
            close_time="22:00",
        ),
        Location(
            id=seed_id("location", "airport"),
            name="4 Chavchavadze Avenue, Tbilisi",
            address="4 Chavchavadze Avenue, Tbilisi",
            description="Fast-service location inside the international terminal.",
            image_url="http://epam-restaurantapp-dev-eu-west-3-frontend.s3-website.eu-west-3.amazonaws.com/location_img.jpg",
            open_time="06:00",
            close_time="23:00",
        ),
    ]

    with table.batch_writer() as batch:
        for loc in locations:
            batch.put_item(Item=loc.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(locations)} locations")
    context["locations"] = {loc.id: loc for loc in locations}

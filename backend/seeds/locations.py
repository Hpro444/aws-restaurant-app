"""Seed module for restaurant locations."""

from datetime import datetime

from domain.location import Location  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed restaurant locations and write them to context['locations']."""
    table = dynamodb.Table(tables["locations"])

    locations = [
        Location(
            id=seed_id("location", "downtown"),
            name="48 Rustaveli Avenue, Tbilisi",
            address="48 Rustaveli Avenue, Tbilisi",
            description="Central city location near the main square.",
            image_url="http://epam-restaurantapp-dev-eu-west-3-frontend.s3-website.eu-west-3.amazonaws.com/location_img.jpg",
            open_time="09:00",
            close_time="23:00",
        ),
        Location(
            id=seed_id("location", "airport"),
            name="4 Chavchavadze Avenue, Tbilisi",
            address="4 Chavchavadze Avenue, Tbilisi",
            description="Fast-service location inside the international terminal.",
            image_url="http://epam-restaurantapp-dev-eu-west-3-frontend.s3-website.eu-west-3.amazonaws.com/location_img.jpg",
            open_time="08:00",
            close_time="22:00",
        ),
        Location(
            id=seed_id("location", "old-town"),
            name="12 Baratashvili Street, Tbilisi",
            address="12 Baratashvili Street, Tbilisi",
            description="Cozy old-town location with an all-day bistro menu.",
            image_url="http://epam-restaurantapp-dev-eu-west-3-frontend.s3-website.eu-west-3.amazonaws.com/location_img.jpg",
            open_time="07:00",
            close_time="21:00",
        ),
    ]

    for location in locations:
        start = datetime.combine(datetime.today(), location.open_time)
        end = datetime.combine(datetime.today(), location.close_time)
        duration_minutes = int((end - start).total_seconds() / 60)
        slot_count = duration_minutes // 105

        if duration_minutes > 16 * 60:
            raise ValueError(f"Working hours exceed 16h for {location.address}")
        if duration_minutes % 105 != 0:
            raise ValueError(
                f"Working hours are not divisible by 105 for {location.address}"
            )
        if slot_count % 2 != 0:
            raise ValueError(
                f"Location must have even slot count per day: {location.address}"
            )

    with table.batch_writer() as batch:
        for loc in locations:
            batch.put_item(Item=loc.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(locations)} locations")
    context["locations"] = {loc.id: loc for loc in locations}

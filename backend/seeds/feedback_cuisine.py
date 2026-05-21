"""Seed module for cuisine feedback."""

from domain.feedback import (
    FeedbackCuisine,  # Updated import  # type: ignore[import-not-found]
)

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 3 cuisine feedback entries per location.

    Requires context['customers'] and context['locations'].
    """
    table = dynamodb.Table(tables["feedback_cuisine"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    alice_id = seed_id("customer", "alice")
    bob_id = seed_id("customer", "bob")
    carol_id = seed_id("customer", "carol")

    entries = [
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "alice:downtown"),
            customer_id=alice_id,
            feedback="Absolutely loved the Pasta Carbonara — rich, creamy, and perfectly cooked. Will definitely be back!",
            location_id=locations[downtown_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "bob:downtown"),
            customer_id=bob_id,
            feedback="The Beef Burger was outstanding. Juicy patty, great toppings. Best burger I've had in the city.",
            location_id=locations[downtown_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "carol:downtown"),
            customer_id=carol_id,
            feedback="Caesar Salad was fresh and well-balanced. Would have appreciated a bigger portion for the price.",
            location_id=locations[downtown_id].id,
            rate=3,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "alice:airport"),
            customer_id=alice_id,
            feedback="Fish & Chips were crispy and hot — impressive for an airport kitchen. Tartare sauce was excellent.",
            location_id=locations[airport_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "bob:airport"),
            customer_id=bob_id,
            feedback="Chicken wrap was fresh and filling. Great option when you need something quick before a flight.",
            location_id=locations[airport_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "carol:airport"),
            customer_id=carol_id,
            feedback="Minestrone was hearty and warming. Nice to find a proper home-style soup in an airport.",
            location_id=locations[airport_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "alice:old-town"),
            customer_id=alice_id,
            feedback="Khachapuri was phenomenal - perfectly baked and rich without being too heavy.",
            location_id=locations[old_town_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "bob:old-town"),
            customer_id=bob_id,
            feedback="Khinkali were juicy and flavorful. Great recommendation from the staff.",
            location_id=locations[old_town_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "carol:old-town"),
            customer_id=carol_id,
            feedback="Lobio was comforting and well seasoned, though I wanted a bit more spice.",
            location_id=locations[old_town_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} cuisine feedback entries")

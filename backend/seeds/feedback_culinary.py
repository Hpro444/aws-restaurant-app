"""Seed module for culinary feedback."""

from domain.feedback import FeedbackCulinary  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 3 culinary feedback entries per location.

    Requires context['customers'] and context['locations'].
    """
    table = dynamodb.Table(tables["feedback_culinary"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")

    alice_id = seed_id("customer", "alice")
    bob_id = seed_id("customer", "bob")
    carol_id = seed_id("customer", "carol")

    entries = [
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "alice:downtown"),
            customer_id=alice_id,
            feedback="Absolutely loved the Pasta Carbonara — rich, creamy, and perfectly cooked. Will definitely be back!",
            location_id=locations[downtown_id].id,
            rating=5,
        ),
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "bob:downtown"),
            customer_id=bob_id,
            feedback="The Beef Burger was outstanding. Juicy patty, great toppings. Best burger I've had in the city.",
            location_id=locations[downtown_id].id,
            rating=4,
        ),
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "carol:downtown"),
            customer_id=carol_id,
            feedback="Caesar Salad was fresh and well-balanced. Would have appreciated a bigger portion for the price.",
            location_id=locations[downtown_id].id,
            rating=3,
        ),
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "alice:airport"),
            customer_id=alice_id,
            feedback="Fish & Chips were crispy and hot — impressive for an airport kitchen. Tartare sauce was excellent.",
            location_id=locations[airport_id].id,
            rating=4,
        ),
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "bob:airport"),
            customer_id=bob_id,
            feedback="Chicken wrap was fresh and filling. Great option when you need something quick before a flight.",
            location_id=locations[airport_id].id,
            rating=5,
        ),
        FeedbackCulinary(
            id=seed_id("feedback-culinary", "carol:airport"),
            customer_id=carol_id,
            feedback="Minestrone was hearty and warming. Nice to find a proper home-style soup in an airport.",
            location_id=locations[airport_id].id,
            rating=4,
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} culinary feedback entries")

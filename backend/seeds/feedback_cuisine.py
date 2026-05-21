"""Seed module for cuisine feedback."""

from domain.feedback import FeedbackCuisine  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 10 cuisine feedback entries per location covering all rating levels.

    Requires context['locations'] populated by the locations seeder.
    """
    table = dynamodb.Table(tables["feedback_cuisine"])
    locations = context["locations"]

    downtown_id = seed_id("location", "downtown")
    airport_id = seed_id("location", "airport")
    old_town_id = seed_id("location", "old-town")

    alice_id = seed_id("customer", "alice")
    bob_id = seed_id("customer", "bob")
    carol_id = seed_id("customer", "carol")
    david_id = seed_id("customer", "david")
    emma_id = seed_id("customer", "emma")
    frank_id = seed_id("customer", "frank")
    grace_id = seed_id("customer", "grace")
    henry_id = seed_id("customer", "henry")
    iris_id = seed_id("customer", "iris")
    james_id = seed_id("customer", "james")
    kate_id = seed_id("customer", "kate")

    entries = [
        # ── Downtown ──────────────────────────────────────────────────────────
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
            id=seed_id("feedback-cuisine", "david:downtown"),
            customer_id=david_id,
            feedback="Extremely disappointing. The pasta was overcooked and the sauce watery. Nothing like the menu description.",
            location_id=locations[downtown_id].id,
            rate=1,
            date="2026-04-15T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "emma:downtown"),
            customer_id=emma_id,
            feedback="The pizza arrived lukewarm and the dough was underbaked. Mediocre at best — expected much more.",
            location_id=locations[downtown_id].id,
            rate=2,
            date="2026-04-18T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "frank:downtown"),
            customer_id=frank_id,
            feedback="Very poor quality this visit. My burger was dry and the fries cold. Complete waste of money.",
            location_id=locations[downtown_id].id,
            rate=1,
            date="2026-04-22T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "grace:downtown"),
            customer_id=grace_id,
            feedback="Below expectations. The soup was bland and the bread stale. Service tried to compensate but the food let it down.",
            location_id=locations[downtown_id].id,
            rate=2,
            date="2026-05-02T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "henry:downtown"),
            customer_id=henry_id,
            feedback="The chocolate mousse with berries was exceptional — light, silky, and beautifully presented. Best dessert in town.",
            location_id=locations[downtown_id].id,
            rate=5,
            date="2026-05-08T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "iris:downtown"),
            customer_id=iris_id,
            feedback="Really enjoyed the Margherita. Fresh mozzarella and the crust had a lovely char. Will be ordering again.",
            location_id=locations[downtown_id].id,
            rate=4,
            date="2026-05-12T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "james:downtown"),
            customer_id=james_id,
            feedback="Decent food overall but nothing exceptional. Portions could be a bit larger for the price charged.",
            location_id=locations[downtown_id].id,
            rate=3,
            date="2026-05-16T00:00:00Z",
        ),
        # ── Airport ───────────────────────────────────────────────────────────
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
            id=seed_id("feedback-cuisine", "kate:airport"),
            customer_id=kate_id,
            feedback="Terrible experience. Cold food, rude staff, and a very long wait. Not acceptable for the prices charged.",
            location_id=locations[airport_id].id,
            rate=1,
            date="2026-04-10T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "james:airport"),
            customer_id=james_id,
            feedback="The fish was overcooked and the chips soggy. Expected much better given the menu price.",
            location_id=locations[airport_id].id,
            rate=2,
            date="2026-04-14T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "iris:airport"),
            customer_id=iris_id,
            feedback="Long wait, order came out wrong, and the replacement was also incorrect. Very frustrating experience.",
            location_id=locations[airport_id].id,
            rate=1,
            date="2026-04-20T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "henry:airport"),
            customer_id=henry_id,
            feedback="Bland and uninspiring. The Greek salad was wilted and the dressing too acidic. Disappointing.",
            location_id=locations[airport_id].id,
            rate=2,
            date="2026-05-01T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "grace:airport"),
            customer_id=grace_id,
            feedback="The sweet potato lentil salad was a genuine surprise — packed with flavour and very satisfying for a light meal.",
            location_id=locations[airport_id].id,
            rate=5,
            date="2026-05-07T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "frank:airport"),
            customer_id=frank_id,
            feedback="Good club sandwich with generous portions. Exactly what you need during a long-haul layover.",
            location_id=locations[airport_id].id,
            rate=4,
            date="2026-05-11T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "emma:airport"),
            customer_id=emma_id,
            feedback="Average experience overall. Food was acceptable but nothing memorable. Fine for an airport setting.",
            location_id=locations[airport_id].id,
            rate=3,
            date="2026-05-15T00:00:00Z",
        ),
        # ── Old Town ──────────────────────────────────────────────────────────
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "alice:old-town"),
            customer_id=alice_id,
            feedback="Khachapuri was phenomenal — perfectly baked and rich without being too heavy.",
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
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "david:old-town"),
            customer_id=david_id,
            feedback="Food was cold and portions disappointingly small. Paid tourist prices for below-average quality.",
            location_id=locations[old_town_id].id,
            rate=1,
            date="2026-04-12T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "emma:old-town"),
            customer_id=emma_id,
            feedback="Expected authentic Georgian flavours but everything tasted quite generic. The Khinkali lacked seasoning.",
            location_id=locations[old_town_id].id,
            rate=2,
            date="2026-04-16T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "frank:old-town"),
            customer_id=frank_id,
            feedback="Rude staff and overcooked Mtsvadi. Very disappointed — this place has gone downhill.",
            location_id=locations[old_town_id].id,
            rate=1,
            date="2026-04-21T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "grace:old-town"),
            customer_id=grace_id,
            feedback="The Lobio was underseasoned and the cornbread dry. Overall below average for the area.",
            location_id=locations[old_town_id].id,
            rate=2,
            date="2026-05-03T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "henry:old-town"),
            customer_id=henry_id,
            feedback="The pineapple tart with vanilla soufflé was simply divine — perfectly balanced and beautifully presented.",
            location_id=locations[old_town_id].id,
            rate=5,
            date="2026-05-09T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "iris:old-town"),
            customer_id=iris_id,
            feedback="Authentic and delicious Georgian food. The Adjarian Khachapuri was the undisputed highlight of the evening.",
            location_id=locations[old_town_id].id,
            rate=4,
            date="2026-05-13T00:00:00Z",
        ),
        FeedbackCuisine(
            id=seed_id("feedback-cuisine", "james:old-town"),
            customer_id=james_id,
            feedback="Decent Georgian food but the service was slow and the atmosphere a bit noisy. Would still try again.",
            location_id=locations[old_town_id].id,
            rate=3,
            date="2026-05-17T00:00:00Z",
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} cuisine feedback entries (10 per location)")

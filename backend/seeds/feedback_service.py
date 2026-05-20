"""Seed module for service feedback."""

from domain.feedback import (
    FeedbackService,  # Updated import  # type: ignore[import-not-found]
)

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 2–3 service feedback entries per waiter.

    Requires context['waiters'].
    """
    table = dynamodb.Table(tables["feedback_service"])
    waiters = context["waiters"]

    lea_id = seed_id("waiter", "lea")
    max_id = seed_id("waiter", "max")

    alice_id = seed_id("customer", "alice")
    bob_id = seed_id("customer", "bob")
    carol_id = seed_id("customer", "carol")

    entries = [
        FeedbackService(
            id=seed_id("feedback-service", "alice:lea"),
            customer_id=alice_id,
            feedback="Lea was wonderful — very attentive, friendly, and knew the menu inside out. Made our evening special.",
            waiter_id=waiters[lea_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "bob:lea"),
            customer_id=bob_id,
            feedback="Professional service throughout. Lea kept our glasses topped up without being asked. Highly recommend.",
            waiter_id=waiters[lea_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "carol:lea"),
            customer_id=carol_id,
            feedback="Very warm and welcoming. Lea remembered my dietary preferences from a previous visit — impressive.",
            waiter_id=waiters[lea_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "alice:max"),
            customer_id=alice_id,
            feedback="Max was efficient and knowledgeable about the menu. Quick service, which is exactly what you need at an airport.",
            waiter_id=waiters[max_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "carol:max"),
            customer_id=carol_id,
            feedback="Max handled a large group smoothly and kept everyone's orders straight. Great under pressure.",
            waiter_id=waiters[max_id].id,
            rate=3,
            date="2026-05-20T00:00:00Z",
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} service feedback entries")

"""Seed module for service feedback."""

from domain.feedback import FeedbackService  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 10 service feedback entries per waiter covering all rating levels.

    Requires context['waiters'] populated by the waiters seeder.
    """
    table = dynamodb.Table(tables["feedback_service"])
    waiters = context["waiters"]

    lea_id = seed_id("waiter", "lea")
    max_id = seed_id("waiter", "max")
    nina_id = seed_id("waiter", "nina")

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
        # ── Lea (Downtown) ────────────────────────────────────────────────────
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
            id=seed_id("feedback-service", "david:lea"),
            customer_id=david_id,
            feedback="Very slow service. Waited over 20 minutes to even be noticed. Completely unacceptable on a quiet evening.",
            waiter_id=waiters[lea_id].id,
            rate=1,
            date="2026-04-13T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "emma:lea"),
            customer_id=emma_id,
            feedback="Lea got our order wrong twice and seemed distracted throughout the meal. Disappointing experience.",
            waiter_id=waiters[lea_id].id,
            rate=2,
            date="2026-04-19T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "frank:lea"),
            customer_id=frank_id,
            feedback="Exceptional service from Lea tonight. Went above and beyond to make our anniversary dinner truly special.",
            waiter_id=waiters[lea_id].id,
            rate=5,
            date="2026-04-27T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "grace:lea"),
            customer_id=grace_id,
            feedback="Friendly and efficient. Lea recommended the daily special which turned out to be excellent.",
            waiter_id=waiters[lea_id].id,
            rate=4,
            date="2026-05-05T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "henry:lea"),
            customer_id=henry_id,
            feedback="Service was average. Nothing went wrong but nothing stood out either. Polite but not engaging.",
            waiter_id=waiters[lea_id].id,
            rate=3,
            date="2026-05-09T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "iris:lea"),
            customer_id=iris_id,
            feedback="Lea made us feel so welcome from the moment we arrived. Truly excellent hospitality.",
            waiter_id=waiters[lea_id].id,
            rate=5,
            date="2026-05-14T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "james:lea"),
            customer_id=james_id,
            feedback="Had to ask multiple times for the bill. Service felt rushed and inattentive during peak hours.",
            waiter_id=waiters[lea_id].id,
            rate=2,
            date="2026-05-18T00:00:00Z",
        ),
        # ── Max (Airport) ─────────────────────────────────────────────────────
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
        FeedbackService(
            id=seed_id("feedback-service", "david:max"),
            customer_id=david_id,
            feedback="Max was rude and dismissive when we asked about allergens. Completely unprofessional attitude.",
            waiter_id=waiters[max_id].id,
            rate=1,
            date="2026-04-11T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "emma:max"),
            customer_id=emma_id,
            feedback="Order took far too long and arrived cold. Max offered no explanation or apology whatsoever.",
            waiter_id=waiters[max_id].id,
            rate=2,
            date="2026-04-17T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "frank:max"),
            customer_id=frank_id,
            feedback="Outstanding service from Max. Handled a complicated multi-course order with grace and great humour.",
            waiter_id=waiters[max_id].id,
            rate=5,
            date="2026-04-24T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "grace:max"),
            customer_id=grace_id,
            feedback="Max was helpful and kept us informed about wait times. Good professional attitude throughout.",
            waiter_id=waiters[max_id].id,
            rate=4,
            date="2026-05-03T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "henry:max"),
            customer_id=henry_id,
            feedback="Max is a star — attentive, knowledgeable, and genuinely made the whole layover experience enjoyable.",
            waiter_id=waiters[max_id].id,
            rate=5,
            date="2026-05-07T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "iris:max"),
            customer_id=iris_id,
            feedback="Adequate service. Max was polite but not particularly engaging or proactive. Got the job done.",
            waiter_id=waiters[max_id].id,
            rate=3,
            date="2026-05-11T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "james:max"),
            customer_id=james_id,
            feedback="Forgotten order, no apology, and wrong dish delivered as the replacement. Terrible experience.",
            waiter_id=waiters[max_id].id,
            rate=1,
            date="2026-05-15T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "kate:max"),
            customer_id=kate_id,
            feedback="Efficient service. Max kept our table well attended despite being clearly very busy.",
            waiter_id=waiters[max_id].id,
            rate=4,
            date="2026-05-19T00:00:00Z",
        ),
        # ── Nina (Old Town) ───────────────────────────────────────────────────
        FeedbackService(
            id=seed_id("feedback-service", "alice:nina"),
            customer_id=alice_id,
            feedback="Nina was very kind and gave excellent pairing suggestions for local dishes.",
            waiter_id=waiters[nina_id].id,
            rate=5,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "bob:nina"),
            customer_id=bob_id,
            feedback="Quick and friendly service from Nina, everything arrived hot and on time.",
            waiter_id=waiters[nina_id].id,
            rate=4,
            date="2026-05-20T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "david:nina"),
            customer_id=david_id,
            feedback="Nina was nowhere to be found for most of our meal. Had to flag down other staff repeatedly.",
            waiter_id=waiters[nina_id].id,
            rate=1,
            date="2026-04-12T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "emma:nina"),
            customer_id=emma_id,
            feedback="Our food arrived at different times and Nina seemed unbothered about it. Not a great experience.",
            waiter_id=waiters[nina_id].id,
            rate=2,
            date="2026-04-18T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "frank:nina"),
            customer_id=frank_id,
            feedback="Nina provided the best restaurant service I have experienced in a long time. Truly wonderful.",
            waiter_id=waiters[nina_id].id,
            rate=5,
            date="2026-04-25T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "grace:nina"),
            customer_id=grace_id,
            feedback="Nina was warm and attentive. Her recommendation for the Georgian wine was absolutely perfect.",
            waiter_id=waiters[nina_id].id,
            rate=4,
            date="2026-05-04T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "henry:nina"),
            customer_id=henry_id,
            feedback="Absolutely charming service. Nina made the whole dinner feel like a special occasion.",
            waiter_id=waiters[nina_id].id,
            rate=5,
            date="2026-05-08T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "iris:nina"),
            customer_id=iris_id,
            feedback="Decent but forgettable service. Nina was polite but not particularly helpful or attentive.",
            waiter_id=waiters[nina_id].id,
            rate=3,
            date="2026-05-12T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "james:nina"),
            customer_id=james_id,
            feedback="Nina seemed more interested in chatting with coworkers than attending to our table. Frustrating.",
            waiter_id=waiters[nina_id].id,
            rate=2,
            date="2026-05-16T00:00:00Z",
        ),
        FeedbackService(
            id=seed_id("feedback-service", "kate:nina"),
            customer_id=kate_id,
            feedback="Very pleasant service. Nina was knowledgeable about the menu and genuinely friendly throughout.",
            waiter_id=waiters[nina_id].id,
            rate=4,
            date="2026-05-19T00:00:00Z",
        ),
    ]

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} service feedback entries (10 per waiter)")

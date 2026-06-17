"""Seed module for service feedback."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from domain.feedback import FeedbackService  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

_SERVICE_COMMENTS = [
    "Attentive and professional service throughout the visit.",
    "Service was friendly and quick, with helpful recommendations.",
    "Great waiter support, everything arrived on time.",
    "Polite service and clear communication during the meal.",
]


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed one service feedback per reservation using reservation-based deterministic IDs.

    This aligns seed IDs with runtime duplicate-prevention logic:
    ``uuid5(NAMESPACE_URL, f"service:{reservation_id}")``.

    Requires context['reservations'] and context['customers'].
    """
    table = dynamodb.Table(tables["feedback_service"])

    reservations = context.get("reservations", [])
    customers = context.get("customers", {})
    customer_by_id = {customer.id: customer for customer in customers.values()}

    if not reservations:
        print("  ! Skipping service feedback seed: no reservations in context")
        return

    entries: list[FeedbackService] = []
    for index, reservation in enumerate(reservations):
        if reservation.status != ReservationStatus.FINISHED:
            continue

        if reservation.waiter_id is None:
            continue

        customer = customer_by_id.get(reservation.customer_id)
        comment = _SERVICE_COMMENTS[index % len(_SERVICE_COMMENTS)]
        rating = 3 + (uuid5(NAMESPACE_URL, f"service-rate:{reservation.id}").int % 3)
        user_name = None
        if customer is not None:
            user_name = f"{customer.fname} {customer.lname}"

        entries.append(
            FeedbackService(
                id=uuid5(NAMESPACE_URL, f"service:{reservation.id}"),
                reservation_id=reservation.id,
                customer_id=reservation.customer_id,
                user_name=user_name,
                user_image_url=customer.image_url if customer else None,
                feedback=comment,
                waiter_id=reservation.waiter_id,
                rate=rating,
                date=reservation.created_at,
            )
        )

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} service feedback entries (max 1 per reservation)")
    context["feedback_service"] = entries

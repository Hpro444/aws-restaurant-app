"""Seed module for cuisine feedback."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from domain.feedback import FeedbackCuisine  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

_CULINARY_COMMENTS = [
    "Food quality was excellent and beautifully presented.",
    "Well-balanced flavors and fresh ingredients.",
    "Very satisfying meal with authentic taste.",
    "Great dish quality and consistent kitchen execution.",
]


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed one culinary feedback per reservation using reservation-based deterministic IDs.

    This aligns seed IDs with runtime duplicate-prevention logic:
    ``uuid5(NAMESPACE_URL, f"culinary:{reservation_id}")``.

    Requires context['reservations'], context['customers'], context['slots'], and context['tables'].
    """
    table = dynamodb.Table(tables["feedback_cuisine"])

    reservations = context.get("reservations", [])
    customers = context.get("customers", {})
    slots = context.get("slots", [])
    tables_list = context.get("tables", [])

    customer_by_id = {customer.id: customer for customer in customers.values()}
    slots_by_id = {slot.id: slot for slot in slots}
    tables_by_id = {table_obj.id: table_obj for table_obj in tables_list}

    if not reservations:
        print("  ! Skipping cuisine feedback seed: no reservations in context")
        return

    entries: list[FeedbackCuisine] = []
    for index, reservation in enumerate(reservations):
        if reservation.status != ReservationStatus.FINISHED:
            continue

        if not reservation.slot_ids:
            continue

        first_slot = slots_by_id.get(reservation.slot_ids[0])
        if first_slot is None:
            continue

        table_obj = tables_by_id.get(first_slot.table_id)
        if table_obj is None:
            continue

        customer = customer_by_id.get(reservation.customer_id)
        comment = _CULINARY_COMMENTS[index % len(_CULINARY_COMMENTS)]
        rating = 3 + (uuid5(NAMESPACE_URL, f"culinary-rate:{reservation.id}").int % 3)
        user_name = None
        if customer is not None:
            user_name = f"{customer.fname} {customer.lname}"

        entries.append(
            FeedbackCuisine(
                id=uuid5(NAMESPACE_URL, f"culinary:{reservation.id}"),
                reservation_id=reservation.id,
                customer_id=reservation.customer_id,
                user_name=user_name,
                user_image_url=customer.image_url if customer else None,
                feedback=comment,
                location_id=table_obj.location_id,
                rate=rating,
                date=reservation.created_at,
            )
        )

    with table.batch_writer() as batch:
        for entry in entries:
            batch.put_item(Item=entry.model_dump(mode="json"))

    print(f"  ✓ Seeded {len(entries)} cuisine feedback entries (max 1 per reservation)")

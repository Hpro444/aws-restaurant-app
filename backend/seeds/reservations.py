"""Seed module for reservations."""

from datetime import datetime, timezone

from domain.reservation import Reservation  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 3 mock reservations: RESERVED, IN_PROGRESS, and CANCELLED.

    Requires context['slots'].
    """
    table = dynamodb.Table(tables["reservations"])
    slots_list = context["slots"]

    if len(slots_list) < 15:
        print("  ! Skipping reservations seed: not enough slots generated")
        return

    # First slots of table #1, #2, and #3 respectively.
    chosen_slots = [slots_list[0], slots_list[7], slots_list[14]]
    created_at = datetime.now(timezone.utc)

    reservations = [
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[0].id}:reserved"),
            customer_id=seed_id("customer", "alice"),
            waiter_id=seed_id("waiter", "lea"),
            created_at=created_at,
            slot=chosen_slots[0].id,
            status=ReservationStatus.RESERVED,
            number_of_guests=4,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[1].id}:in-progress"),
            customer_id=seed_id("customer", "bob"),
            waiter_id=seed_id("waiter", "max"),
            created_at=created_at,
            slot=chosen_slots[1].id,
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[2].id}:cancelled"),
            customer_id=seed_id("customer", "carol"),
            waiter_id=None,
            created_at=created_at,
            slot=chosen_slots[2].id,
            status=ReservationStatus.CANCELLED,
            number_of_guests=3,
        ),
    ]

    with table.batch_writer() as batch:
        for reservation in reservations:
            batch.put_item(Item=reservation.model_dump(mode="json"))

    print(
        f"  ✓ Seeded {len(reservations)} reservations (2 active, 1 cancelled for testing)"
    )

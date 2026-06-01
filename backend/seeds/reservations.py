"""Seed module for reservations."""

from datetime import datetime, timezone

from domain.reservation import Reservation  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]
from enums.slot_status import SlotStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed 3 mock reservations: RESERVED, IN_PROGRESS, and CANCELLED.

    Also flips the status of the slots held by the two active reservations
    (RESERVED, IN_PROGRESS) to :attr:`SlotStatus.RESERVED` so demo
    availability queries — which now read directly from ``slot.status`` —
    reflect those bookings. The CANCELLED reservation's slot stays FREE.

    Requires context['slots'].
    """
    reservations_table = dynamodb.Table(tables["reservations"])
    slots_table = dynamodb.Table(tables["slots"])
    slots_list = context["slots"]
    customers = context["customers"]
    waiters = context["waiters"]

    if len(slots_list) < 15:
        print("  ! Skipping reservations seed: not enough slots generated")
        return

    # First slots of table #1, #2, and #3 respectively.
    chosen_slots = [slots_list[0], slots_list[7], slots_list[14]]
    created_at = datetime.now(timezone.utc)

    reservations = [
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[0].id}:reserved"),
            customer_id=customers["alice@example.com"].id,
            waiter_id=waiters["lea@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[0].id],
            status=ReservationStatus.RESERVED,
            number_of_guests=4,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[1].id}:in-progress"),
            customer_id=customers["bob@example.com"].id,
            waiter_id=waiters["max@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[1].id],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[2].id}:cancelled"),
            customer_id=customers["carol@example.com"].id,
            waiter_id=None,
            created_at=created_at,
            slot_ids=[chosen_slots[2].id],
            status=ReservationStatus.CANCELLED,
            number_of_guests=3,
        ),
    ]

    with reservations_table.batch_writer() as batch:
        for reservation in reservations:
            batch.put_item(Item=to_item(reservation))

    # Flip the slots claimed by active reservations to RESERVED so
    # availability queries reflect the demo bookings.
    active_slots = [chosen_slots[0], chosen_slots[1]]
    with slots_table.batch_writer() as batch:
        for slot in active_slots:
            slot.status = SlotStatus.RESERVED
            batch.put_item(Item=to_item(slot))

    print(
        f"  ✓ Seeded {len(reservations)} reservations "
        "(2 active, 1 cancelled for testing) and flipped 2 slots to RESERVED"
    )
    context["reservations"] = reservations

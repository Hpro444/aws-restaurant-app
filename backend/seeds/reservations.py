"""Seed module for reservations."""

from datetime import datetime, timezone

from domain.reservation import Reservation  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]
from enums.slot_status import SlotStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed explicit mock reservations across statuses.

    Also flips the status of slots held by active reservations
    (RESERVED, IN_PROGRESS) to :attr:`SlotStatus.RESERVED` so demo
    availability queries — which now read directly from ``slot.status`` —
    reflect those bookings. FINISHED and CANCELLED reservations keep slots FREE.

    Requires context['slots'].
    """
    reservations_table = dynamodb.Table(tables["reservations"])
    slots_table = dynamodb.Table(tables["slots"])
    slots_list = context["slots"]
    customers = context["customers"]
    waiters = context["waiters"]

    if len(slots_list) < 17:
        print("  ! Skipping reservations seed: not enough slots generated")
        return

    # Keep the explicit slot-picking pattern used previously and extend it.
    # First, second, and third slots of table #1, #2, #3.
    chosen_slots = [
        slots_list[0],
        slots_list[7],
        slots_list[14],
        slots_list[1],
        slots_list[8],
        slots_list[15],
        slots_list[2],
        slots_list[9],
        slots_list[16],
    ]
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
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[3].id}:finished"),
            customer_id=customers["david@example.com"].id,
            waiter_id=waiters["lea@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[3].id],
            status=ReservationStatus.FINISHED,
            number_of_guests=5,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[4].id}:finished"),
            customer_id=customers["emma@example.com"].id,
            waiter_id=waiters["max@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[4].id],
            status=ReservationStatus.FINISHED,
            number_of_guests=2,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[5].id}:reserved"),
            customer_id=customers["frank@example.com"].id,
            waiter_id=waiters["nina@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[5].id],
            status=ReservationStatus.RESERVED,
            number_of_guests=6,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[6].id}:finished"),
            customer_id=customers["grace@example.com"].id,
            waiter_id=waiters["lea@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[6].id],
            status=ReservationStatus.FINISHED,
            number_of_guests=4,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[7].id}:in-progress"),
            customer_id=customers["henry@example.com"].id,
            waiter_id=waiters["max@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[7].id],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=3,
        ),
        Reservation(
            id=seed_id("reservation", f"{chosen_slots[8].id}:finished"),
            customer_id=customers["iris@example.com"].id,
            waiter_id=waiters["nina@example.com"].id,
            created_at=created_at,
            slot_ids=[chosen_slots[8].id],
            status=ReservationStatus.FINISHED,
            number_of_guests=2,
        ),
    ]

    with reservations_table.batch_writer() as batch:
        for reservation in reservations:
            batch.put_item(Item=to_item(reservation))

    # Flip the slots claimed by active reservations to RESERVED so
    # availability queries reflect the demo bookings.
    active_slots = [
        chosen_slots[0],
        chosen_slots[1],
        chosen_slots[5],
        chosen_slots[7],
    ]
    with slots_table.batch_writer() as batch:
        for slot in active_slots:
            slot.status = SlotStatus.RESERVED
            batch.put_item(Item=to_item(slot))

    print(
        f"  ✓ Seeded {len(reservations)} reservations "
        f"({len(active_slots)} active, "
        f"{sum(1 for r in reservations if r.status == ReservationStatus.FINISHED)} finished, "
        f"{sum(1 for r in reservations if r.status == ReservationStatus.CANCELLED)} cancelled) "
        f"and flipped {len(active_slots)} slots to RESERVED"
    )

    # Expose the created reservations so the waiter-view projection seeder can
    # build its denormalized rows from the same data.
    context["reservations"] = reservations

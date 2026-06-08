"""Seed module for reservations."""

from datetime import datetime, time, timezone

from domain.reservation import Reservation  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]
from enums.slot_status import SlotStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def _first_day_slot(slots_list: list, waiter_id, target_date, slot_index: int = 0):
    """Return the nth earliest slot for a waiter on target_date.

    Args:
        slots_list: All seeded Slot objects.
        waiter_id: UUID of the waiter to filter by.
        target_date: The calendar date to look up (a ``date`` object).
        slot_index: Which slot to return when sorted by start_time (default 0 = first).

    Returns:
        Matching Slot, or None if fewer than slot_index+1 slots exist.

    """
    matching = sorted(
        [
            s
            for s in slots_list
            if s.waiter_id == waiter_id and s.date.date() == target_date
        ],
        key=lambda s: s.start_time,
    )
    return matching[slot_index] if len(matching) > slot_index else None


def _seed_past_reservations(
    slots_list: list, customers: dict, today
) -> list[Reservation]:
    """Create one FINISHED reservation per waiter per past date.

    Iterates all past slots, groups by (date, waiter_id) and picks the earliest
    slot per group.  Each resulting reservation carries a ``date`` field and a
    ``created_at`` set to noon UTC on that day so period-based GSI queries and
    report aggregations land in the correct ISO week.

    Args:
        slots_list: All seeded Slot objects (past and future mixed).
        customers: Dict keyed by email containing all Customer objects.
        today: The current UTC date (``datetime.date``).

    Returns:
        List of FINISHED Reservation objects for all past (date, waiter) pairs.

    """
    customer_list = list(customers.values())

    # For each (date, waiter_id) pair keep only the earliest slot of the day.
    waiter_day_slot: dict = {}
    for slot in slots_list:
        if slot.waiter_id is None:
            continue
        slot_date = slot.date.date()
        if slot_date >= today:
            continue
        key = (slot_date, slot.waiter_id)
        if (
            key not in waiter_day_slot
            or slot.start_time < waiter_day_slot[key].start_time
        ):
            waiter_day_slot[key] = slot

    past_reservations: list[Reservation] = []
    for i, ((slot_date, waiter_id), slot) in enumerate(sorted(waiter_day_slot.items())):
        customer = customer_list[i % len(customer_list)]
        created_at = datetime.combine(slot_date, time(12, 0), tzinfo=timezone.utc)
        past_reservations.append(
            Reservation(
                id=seed_id("reservation", f"{slot.id}:past"),
                customer_id=customer.id,
                waiter_id=waiter_id,
                created_at=created_at,
                slot_ids=[slot.id],
                status=ReservationStatus.FINISHED,
                number_of_guests=2 + (i % 4),
                date=slot_date.isoformat(),
            )
        )

    return past_reservations


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed today's showcase reservations plus past FINISHED reservations for delta testing.

    Today's nine reservations cover every status (RESERVED, IN_PROGRESS, FINISHED,
    CANCELLED) across all three locations and are selected by explicit waiter/date
    filtering — not by fragile list indices — so they remain stable when the slot
    list grows with past days.

    Past reservations (one FINISHED per waiter per past day) provide the historical
    data needed to compute meaningful current-vs-previous-week deltas in the waiter
    and location reports.

    Active slots (RESERVED / IN_PROGRESS) are flipped to SlotStatus.RESERVED so
    availability queries reflect the demo bookings.

    Requires context['slots'], context['customers'], and context['waiters'].
    """
    reservations_table = dynamodb.Table(tables["reservations"])
    slots_table = dynamodb.Table(tables["slots"])
    slots_list = context["slots"]
    customers = context["customers"]
    waiters = context["waiters"]

    today = datetime.now(timezone.utc).date()
    created_at = datetime.now(timezone.utc)

    def pick(waiter_email: str, idx: int = 0):
        """Return idx-th today slot for the named waiter."""
        return _first_day_slot(slots_list, waiters[waiter_email].id, today, idx)

    # ── Today's showcase reservations ──────────────────────────────────────
    # Downtown first shift (tables 1-3): lea.  Tables 4-6: charlie.
    # Downtown second shift (tables 1-3): olivia.  Tables 4-6: ethan.
    # Airport first shift: max / sofia.  Second shift: liam / mia.
    # Old Town first shift: nina / noah.  Second shift: ava / luka.
    s_lea = pick("lea@example.com")  # Downtown 1st shift → RESERVED
    s_olivia = pick("olivia@example.com")  # Downtown 2nd shift → IN_PROGRESS
    s_charlie = pick("charlie@example.com")  # Downtown 1st shift (t4-6) → CANCELLED
    s_max = pick("max@example.com")  # Airport 1st shift → FINISHED
    s_liam = pick("liam@example.com")  # Airport 2nd shift → FINISHED
    s_mia = pick("mia@example.com")  # Airport 2nd shift (t4-6) → RESERVED
    s_nina = pick("nina@example.com")  # Old Town 1st shift → FINISHED
    s_ava = pick("ava@example.com")  # Old Town 2nd shift → IN_PROGRESS
    s_noah = pick("noah@example.com")  # Old Town 1st shift (t4-6) → FINISHED

    today_slots = [
        s_lea,
        s_olivia,
        s_charlie,
        s_max,
        s_liam,
        s_mia,
        s_nina,
        s_ava,
        s_noah,
    ]
    if any(s is None for s in today_slots):
        missing = [
            name
            for name, s in zip(
                [
                    "lea",
                    "olivia",
                    "charlie",
                    "max",
                    "liam",
                    "mia",
                    "nina",
                    "ava",
                    "noah",
                ],
                today_slots,
            )
            if s is None
        ]
        print(f"  ! Skipping today's reservations: no slots found for {missing}")
        context["reservations"] = []
        return

    today_str = today.isoformat()
    reservations: list[Reservation] = [
        Reservation(
            id=seed_id("reservation", f"{s_lea.id}:reserved"),
            customer_id=customers["alice@example.com"].id,
            waiter_id=s_lea.waiter_id,
            created_at=created_at,
            slot_ids=[s_lea.id],
            status=ReservationStatus.RESERVED,
            number_of_guests=4,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_olivia.id}:in-progress"),
            customer_id=customers["bob@example.com"].id,
            waiter_id=s_olivia.waiter_id,
            created_at=created_at,
            slot_ids=[s_olivia.id],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_charlie.id}:cancelled"),
            customer_id=customers["carol@example.com"].id,
            waiter_id=s_charlie.waiter_id,
            created_at=created_at,
            slot_ids=[s_charlie.id],
            status=ReservationStatus.CANCELLED,
            number_of_guests=3,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_max.id}:finished"),
            customer_id=customers["david@example.com"].id,
            waiter_id=s_max.waiter_id,
            created_at=created_at,
            slot_ids=[s_max.id],
            status=ReservationStatus.FINISHED,
            number_of_guests=5,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_liam.id}:finished"),
            customer_id=customers["emma@example.com"].id,
            waiter_id=s_liam.waiter_id,
            created_at=created_at,
            slot_ids=[s_liam.id],
            status=ReservationStatus.FINISHED,
            number_of_guests=2,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_mia.id}:reserved"),
            customer_id=customers["frank@example.com"].id,
            waiter_id=s_mia.waiter_id,
            created_at=created_at,
            slot_ids=[s_mia.id],
            status=ReservationStatus.RESERVED,
            number_of_guests=6,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_nina.id}:finished"),
            customer_id=customers["grace@example.com"].id,
            waiter_id=s_nina.waiter_id,
            created_at=created_at,
            slot_ids=[s_nina.id],
            status=ReservationStatus.FINISHED,
            number_of_guests=4,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_ava.id}:in-progress"),
            customer_id=customers["henry@example.com"].id,
            waiter_id=s_ava.waiter_id,
            created_at=created_at,
            slot_ids=[s_ava.id],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=3,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_noah.id}:finished"),
            customer_id=customers["iris@example.com"].id,
            waiter_id=s_noah.waiter_id,
            created_at=created_at,
            slot_ids=[s_noah.id],
            status=ReservationStatus.FINISHED,
            number_of_guests=2,
            date=today_str,
        ),
    ]

    # ── Past FINISHED reservations (delta testing) ─────────────────────────
    past_reservations = _seed_past_reservations(slots_list, customers, today)

    all_reservations = reservations + past_reservations

    with reservations_table.batch_writer() as batch:
        for reservation in all_reservations:
            batch.put_item(Item=to_item(reservation))

    # Flip today's active slots to RESERVED so availability queries are correct.
    active_slots = [s_lea, s_olivia, s_mia, s_ava]
    with slots_table.batch_writer() as batch:
        for slot in active_slots:
            slot.status = SlotStatus.RESERVED
            batch.put_item(Item=to_item(slot))

    finished_count = sum(
        1 for r in all_reservations if r.status == ReservationStatus.FINISHED
    )
    print(
        f"  ✓ Seeded {len(reservations)} today's reservations + "
        f"{len(past_reservations)} past FINISHED reservations "
        f"({finished_count} total finished) — "
        f"{len(active_slots)} active slots flipped to RESERVED"
    )

    context["reservations"] = all_reservations

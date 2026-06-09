"""Seed module for reservations."""

from datetime import UTC, datetime, time

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


def _resolve_status(
    slot, intended: ReservationStatus, now: datetime
) -> ReservationStatus:
    """Return IN_PROGRESS when the slot has already started and status is RESERVED."""
    if intended == ReservationStatus.RESERVED and slot.start_time <= now:
        return ReservationStatus.IN_PROGRESS
    return intended


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
    for i, ((slot_date, _waiter_id), slot) in enumerate(
        sorted(waiter_day_slot.items())
    ):
        customer = customer_list[i % len(customer_list)]
        created_at = datetime.combine(slot_date, time(12, 0), tzinfo=UTC)
        past_reservations.append(
            Reservation(
                id=seed_id("reservation", f"{slot.id}:past"),
                customer_id=customer.id,
                waiter_id=slot.waiter_id,
                created_at=created_at,
                slot_ids=[slot.id],
                status=ReservationStatus.FINISHED,
                number_of_guests=2 + (i % 4),
                date=slot_date.isoformat(),
            )
        )

    return past_reservations


def _seed_current_week_finished(
    slots_list: list, customers: dict, today
) -> list[Reservation]:
    """Create 2 FINISHED reservations per waiter per day for Tue–Sun of the current week.

    Skips today to avoid slot conflicts with the showcase reservations. Uses two
    unique start-time slots per (day, waiter) pair so each waiter accumulates at
    least 12 FINISHED reservations within the current ISO week — enough for the
    report seeder to produce meaningful order counts and deltas.

    Args:
        slots_list: All seeded Slot objects (today + 6 days ahead).
        customers: Dict keyed by email containing all Customer objects.
        today: The current UTC date (``datetime.date``).

    Returns:
        List of FINISHED Reservation objects for days 1–6 of the current week.

    """
    customer_list = list(customers.values())

    # Group all slots for days 1–6 (Tue–Sun of current week) by (date, waiter_id).
    waiter_day_slots: dict = {}
    for slot in slots_list:
        if slot.waiter_id is None:
            continue
        slot_date = slot.date.date()
        day_offset = (slot_date - today).days
        if day_offset < 1 or day_offset > 6:
            continue
        key = (slot_date, slot.waiter_id)
        waiter_day_slots.setdefault(key, []).append(slot)

    # Sort each group by start_time so we pick the earliest unique windows.
    for key in waiter_day_slots:
        waiter_day_slots[key].sort(key=lambda s: s.start_time)

    reservations: list[Reservation] = []
    counter = 0
    for (slot_date, waiter_id), day_slots in sorted(waiter_day_slots.items()):
        seen_starts: set = set()
        selected = []
        for slot in day_slots:
            if slot.start_time not in seen_starts:
                seen_starts.add(slot.start_time)
                selected.append(slot)
            if len(selected) >= 2:
                break

        for j, slot in enumerate(selected):
            customer = customer_list[counter % len(customer_list)]
            created_at = datetime.combine(slot_date, time(12, 0), tzinfo=UTC)
            reservations.append(
                Reservation(
                    id=seed_id("reservation", f"{slot.id}:finished-cw-{j}"),
                    customer_id=customer.id,
                    waiter_id=waiter_id,
                    created_at=created_at,
                    slot_ids=[slot.id],
                    status=ReservationStatus.FINISHED,
                    number_of_guests=2 + (counter % 5),
                    date=slot_date.isoformat(),
                )
            )
            counter += 1

    return reservations


def _seed_today_extra_for_lea(
    slots_list: list,
    tables_list: list,
    customers: dict,
    waiters: dict,
    today,
    now: datetime,
) -> list[Reservation]:
    """Create several extra reservations for Lea (Downtown, tables 1-3) today.

    The base showcase seed only books Lea's two earliest 09:00 slots, so the
    waiter table-view (GET /reservations/waiter) is nearly empty whenever a waiter
    queries a specific table or a ``time_from`` later than 09:00. This fills
    tables 1-3 with a handful of reservations spread across the day so the demo
    dashboard is well populated for Lea.

    Slots already used by the base showcase (the 09:00 slots) are skipped to avoid
    double-booking the same slot. Each reservation carries an explicit ``date`` and
    a ``created_at`` of ``now`` so it lands in today's projection rows.

    Args:
        slots_list: All seeded Slot objects.
        tables_list: All seeded Table objects (for table_number lookup).
        customers: Dict keyed by email of Customer objects.
        waiters: Dict keyed by email of Waiter objects.
        today: The current UTC date (``datetime.date``).
        now: The current UTC datetime (for RESERVED -> IN_PROGRESS resolution).

    Returns:
        List of Reservation objects for Lea across tables 1-3 today.

    """
    lea = waiters.get("lea@example.com")
    if lea is None:
        return []

    table_number_by_id = {t.id: t.table_number for t in tables_list}
    customer_list = list(customers.values())
    if not customer_list:
        return []

    # Lea's today slots grouped by table number, each sorted by start_time.
    slots_by_table: dict = {}
    for slot in slots_list:
        if slot.waiter_id != lea.id or slot.date.date() != today:
            continue
        table_number = table_number_by_id.get(slot.table_id)
        if table_number is None:
            continue
        slots_by_table.setdefault(table_number, []).append(slot)
    for table_slots in slots_by_table.values():
        table_slots.sort(key=lambda s: s.start_time)

    today_str = today.isoformat()
    reservations: list[Reservation] = []
    counter = 0
    # Book a few later slots per table so every table and a range of start times
    # are covered. Skip index 0 (09:00) on tables 1 and 2 — already booked by the
    # showcase seed — but keep it on table 3, which the showcase leaves empty.
    for table_number in (1, 2, 3):
        table_slots = slots_by_table.get(table_number, [])
        chosen = table_slots[0:3] if table_number == 3 else table_slots[1:4]
        for slot in chosen:
            customer = customer_list[counter % len(customer_list)]
            reservations.append(
                Reservation(
                    id=seed_id("reservation", f"{slot.id}:lea-extra"),
                    customer_id=customer.id,
                    waiter_id=lea.id,
                    created_at=now,
                    slot_ids=[slot.id],
                    status=_resolve_status(slot, ReservationStatus.RESERVED, now),
                    number_of_guests=2 + (counter % 4),
                    date=today_str,
                )
            )
            counter += 1

    return reservations


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

    now = datetime.now(UTC)
    today = now.date()
    created_at = now

    def pick(waiter_email: str, idx: int = 0):
        """Return idx-th today slot for the named waiter."""
        return _first_day_slot(slots_list, waiters[waiter_email].id, today, idx)

    # ── Today's showcase reservations ──────────────────────────────────────
    # Downtown first shift (tables 1-3): lea.  Tables 4-6: charlie.
    # Downtown second shift (tables 1-3): olivia.  Tables 4-6: ethan.
    # Airport first shift: max / sofia.  Second shift: liam / mia.
    # Old Town first shift: nina / noah.  Second shift: ava / luka.
    s_lea = pick("lea@example.com")  # Downtown 1st shift → RESERVED
    s_lea2 = pick(
        "lea@example.com", 1
    )  # Downtown 1st shift (2nd slot) → RESERVED (visitor)
    s_olivia = pick("olivia@example.com")  # Downtown 2nd shift → IN_PROGRESS
    s_charlie = pick("charlie@example.com")  # Downtown 1st shift (t4-6) → CANCELLED
    s_ethan = pick(
        "ethan@example.com"
    )  # Downtown 2nd shift (t4-6) → RESERVED (visitor)
    s_max = pick("max@example.com")  # Airport 1st shift → FINISHED
    s_liam = pick("liam@example.com")  # Airport 2nd shift → FINISHED
    s_mia = pick("mia@example.com")  # Airport 2nd shift (t4-6) → RESERVED
    s_nina = pick("nina@example.com")  # Old Town 1st shift → FINISHED
    s_ava = pick("ava@example.com")  # Old Town 2nd shift → IN_PROGRESS
    s_noah = pick("noah@example.com")  # Old Town 1st shift (t4-6) → FINISHED

    today_slots = [
        s_lea,
        s_lea2,
        s_olivia,
        s_charlie,
        s_ethan,
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
                    "lea2",
                    "olivia",
                    "charlie",
                    "ethan",
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
            id=seed_id("reservation", f"{s_lea2.id}:visitor"),
            customer_id=None,
            client_name="Sofia Greco",
            waiter_id=s_lea2.waiter_id,
            created_at=created_at,
            slot_ids=[s_lea2.id],
            status=_resolve_status(s_lea2, ReservationStatus.RESERVED, now),
            number_of_guests=3,
            date=today_str,
        ),
        Reservation(
            id=seed_id("reservation", f"{s_lea.id}:reserved"),
            customer_id=customers["alice@example.com"].id,
            waiter_id=s_lea.waiter_id,
            created_at=created_at,
            slot_ids=[s_lea.id],
            status=_resolve_status(s_lea, ReservationStatus.RESERVED, now),
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
            id=seed_id("reservation", f"{s_ethan.id}:visitor"),
            customer_id=None,
            client_name="Marco Rossi",
            waiter_id=s_ethan.waiter_id,
            created_at=created_at,
            slot_ids=[s_ethan.id],
            status=_resolve_status(s_ethan, ReservationStatus.RESERVED, now),
            number_of_guests=2,
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
            status=_resolve_status(s_mia, ReservationStatus.RESERVED, now),
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

    # ── Current-week FINISHED reservations (report data) ───────────────────
    # 2 per waiter per day for Tue–Sun → ≥12 FINISHED per waiter this week.
    current_week_finished = _seed_current_week_finished(slots_list, customers, today)

    # ── Extra reservations for Lea today (populate the waiter table-view) ──
    lea_extra = _seed_today_extra_for_lea(
        slots_list, context["tables"], customers, waiters, today, now
    )

    all_reservations = (
        reservations + past_reservations + current_week_finished + lea_extra
    )

    with reservations_table.batch_writer() as batch:
        for reservation in all_reservations:
            batch.put_item(Item=to_item(reservation))

    # Flip slots referenced by all non-cancelled reservations to RESERVED so
    # availability checks see seeded bookings as occupied.
    slots_by_id = {slot.id: slot for slot in slots_list}
    reserved_slot_ids = {
        slot_id
        for reservation in all_reservations
        if reservation.status != ReservationStatus.CANCELLED
        for slot_id in reservation.slot_ids
    }
    occupied_slots = [
        slots_by_id[slot_id] for slot_id in reserved_slot_ids if slot_id in slots_by_id
    ]

    with slots_table.batch_writer() as batch:
        for slot in occupied_slots:
            slot.status = SlotStatus.RESERVED
            batch.put_item(Item=to_item(slot))

    finished_count = sum(
        1 for r in all_reservations if r.status == ReservationStatus.FINISHED
    )
    print(
        f"  ✓ Seeded {len(reservations)} today's reservations + "
        f"{len(past_reservations)} past FINISHED + "
        f"{len(current_week_finished)} current-week FINISHED + "
        f"{len(lea_extra)} extra for Lea today "
        f"({finished_count} total finished) — "
        f"{len(occupied_slots)} occupied slots flipped to RESERVED"
    )

    context["reservations"] = all_reservations

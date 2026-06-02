"""Seed module for the reservation waiter-view projection table."""

from domain.reservation_waiter_view import (  # type: ignore[import-not-found]
    ReservationWaiterView,
)
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

from seeds.utils import to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed the ReservationWaiterView projection for active seeded reservations.

    Mirrors the runtime projection: one flattened row per non-cancelled
    reservation, carrying the denormalized table/location/time data that the
    waiter dashboard reads in a single GSI query. Cancelled reservations are
    intentionally excluded (the runtime deletes their projection rows on
    cancel). The ``location_date`` / ``time_table`` GSI key attributes are
    injected the same way :meth:`ReservationWaiterView.to_dynamodb_item` does.

    Requires context['reservations'], context['slots'], context['tables'],
    and context['locations'].
    """
    view_table = dynamodb.Table(tables["reservation_waiter_view"])

    reservations = context.get("reservations", [])
    slots_by_id = {slot.id: slot for slot in context.get("slots", [])}
    tables_by_id = {table.id: table for table in context.get("tables", [])}
    locations = context.get("locations", {})

    if not reservations:
        print("  ! Skipping reservation waiter-view seed: no reservations in context")
        return

    rows: list[ReservationWaiterView] = []
    for reservation in reservations:
        if reservation.status == ReservationStatus.CANCELLED:
            continue

        reservation_slots = [
            slots_by_id[slot_id]
            for slot_id in reservation.slot_ids
            if slot_id in slots_by_id
        ]
        if not reservation_slots:
            continue

        table = tables_by_id.get(reservation_slots[0].table_id)
        if table is None:
            continue
        location = locations.get(table.location_id)

        start_time = min(slot.start_time for slot in reservation_slots)
        end_time = max(slot.end_time for slot in reservation_slots)

        rows.append(
            ReservationWaiterView(
                id=reservation.id,
                customer_id=reservation.customer_id,
                waiter_id=reservation.waiter_id,
                location_id=table.location_id,
                location_address=location.address if location else None,
                table_number=table.table_number,
                table_name=str(table.table_number),
                date=start_time.date().isoformat(),
                time_from=start_time.strftime("%H:%M"),
                time_to=end_time.strftime("%H:%M"),
                guests_number=reservation.number_of_guests,
                status=reservation.status,
            )
        )

    with view_table.batch_writer() as batch:
        for view in rows:
            item = to_item(view)
            item["location_date"] = ReservationWaiterView.location_date(
                view.location_id, view.date
            )
            item["time_table"] = ReservationWaiterView.time_table(
                view.time_from, view.table_name
            )
            batch.put_item(Item=item)

    print(f"  ✓ Seeded {len(rows)} reservation waiter-view projections")

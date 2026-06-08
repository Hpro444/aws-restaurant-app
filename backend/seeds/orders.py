"""Seed module for orders."""

from datetime import datetime, timezone

from domain.order import Order  # type: ignore[import-not-found]
from domain.order_item import OrderItem  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed demo orders linked to active, reserved, and finished reservations.

    Creates one order per IN_PROGRESS or FINISHED reservation and one for the
    first RESERVED reservation, using dishes from context. Requires
    context['reservations'] and context['dishes'].
    """
    orders_table = dynamodb.Table(tables["orders"])
    reservations = context["reservations"]
    dishes = context["dishes"]

    if not reservations or not dishes:
        print("  ! Skipping orders seed: no reservations or dishes in context")
        return

    active = [r for r in reservations if r.status == ReservationStatus.IN_PROGRESS]
    reserved = [r for r in reservations if r.status == ReservationStatus.RESERVED]
    finished = [r for r in reservations if r.status == ReservationStatus.FINISHED]

    targets = active + reserved[:1] + finished

    if not targets:
        print("  ! Skipping orders seed: no suitable reservations found")
        return

    created_at = datetime.now(timezone.utc)
    orders = []
    for i, reservation in enumerate(targets):
        dish_a = dishes[i % len(dishes)]
        dish_b = dishes[(i + 1) % len(dishes)]
        order = Order(
            id=seed_id("order", str(reservation.id)),
            reservation_id=reservation.id,
            waiter_id=reservation.waiter_id,
            items=[
                OrderItem(dish_id=dish_a.id, quantity=2),
                OrderItem(dish_id=dish_b.id, quantity=1),
            ],
            created_at=created_at,
        )
        orders.append(order)

    with orders_table.batch_writer() as batch:
        for order in orders:
            batch.put_item(Item=to_item(order))

    print(f"  ✓ Seeded {len(orders)} orders")
    context["orders"] = orders

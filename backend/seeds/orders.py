"""Seed module for orders."""

from datetime import datetime, timezone

from domain.order import Order  # type: ignore[import-not-found]
from domain.order_item import OrderItem  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed orders linked to active, reserved, and finished reservations.

    IN_PROGRESS and the first RESERVED reservation each get one order.
    Every FINISHED reservation gets two orders so that ``orders_processed``
    counts in waiter and location reports are meaningfully non-zero.

    Requires context['reservations'] and context['dishes'].
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

    if not active and not reserved and not finished:
        print("  ! Skipping orders seed: no suitable reservations found")
        return

    created_at = datetime.now(timezone.utc)
    orders = []

    # One order each for active and the first reserved reservation.
    for i, reservation in enumerate(active + reserved[:1]):
        dish_a = dishes[i % len(dishes)]
        dish_b = dishes[(i + 1) % len(dishes)]
        orders.append(
            Order(
                id=seed_id("order", str(reservation.id)),
                reservation_id=reservation.id,
                waiter_id=reservation.waiter_id,
                items=[
                    OrderItem(dish_id=dish_a.id, quantity=2),
                    OrderItem(dish_id=dish_b.id, quantity=1),
                ],
                created_at=created_at,
            )
        )

    # Two orders per finished reservation for meaningful report order counts.
    for i, reservation in enumerate(finished):
        for j in range(2):
            dish_a = dishes[(i * 2 + j) % len(dishes)]
            dish_b = dishes[(i * 2 + j + 1) % len(dishes)]
            dish_c = dishes[(i * 2 + j + 2) % len(dishes)]
            orders.append(
                Order(
                    id=seed_id("order", f"{reservation.id}:{j}"),
                    reservation_id=reservation.id,
                    waiter_id=reservation.waiter_id,
                    items=[
                        OrderItem(dish_id=dish_a.id, quantity=1),
                        OrderItem(dish_id=dish_b.id, quantity=2),
                        OrderItem(dish_id=dish_c.id, quantity=1),
                    ],
                    created_at=created_at,
                )
            )

    with orders_table.batch_writer() as batch:
        for order in orders:
            batch.put_item(Item=to_item(order))

    print(
        f"  ✓ Seeded {len(orders)} orders "
        f"({len(finished) * 2} from {len(finished)} FINISHED reservations)"
    )
    context["orders"] = orders

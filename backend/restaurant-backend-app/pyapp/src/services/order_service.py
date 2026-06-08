"""Service layer for creating and managing orders."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from domain.order import Order
from domain.order_item import OrderItem
from dto.orders import CreateOrderRequest, CreateOrderResponse
from enums.http_status_code import HttpStatusCode
from repositories.dish_repository import DishRepository
from repositories.order_repository import OrderRepository
from repositories.reservation_repository import ReservationRepository


class OrderService:
    """Handles order creation with reservation ownership and dish validation."""

    def __init__(
        self,
        settings: AppConfig | None = None,
        order_repository: OrderRepository | None = None,
        reservation_repository: ReservationRepository | None = None,
        dish_repository: DishRepository | None = None,
    ) -> None:
        """Create repository dependencies, creating defaults when omitted.

        Args:
            settings: Shared application config.
            order_repository: Optional OrderRepository instance.
            reservation_repository: Optional ReservationRepository instance.
            dish_repository: Optional DishRepository instance.

        """
        cfg = settings or AppConfig()
        self._order_repo = order_repository or OrderRepository(cfg)
        self._reservation_repo = reservation_repository or ReservationRepository(cfg)
        self._dish_repo = dish_repository or DishRepository(cfg)

    def create_order(
        self, waiter_id: UUID, request: CreateOrderRequest
    ) -> CreateOrderResponse:
        """Create an order for a reservation, scoped to the requesting waiter.

        Validates that:
        - The reservation exists.
        - The requesting waiter is assigned to the reservation.
        - Every dish_id in the item list refers to an existing dish.

        Args:
            waiter_id: UUID of the authenticated waiter creating the order.
            request: Validated request DTO containing reservation_id and items.

        Returns:
            Response DTO with the new order's id and linked reservation_id.

        Raises:
            ApplicationException: 404 if reservation or a dish is not found,
                403 if the waiter is not assigned to the reservation.

        """
        reservation = self._reservation_repo.get(request.reservation_id)
        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                f"Reservation '{request.reservation_id}' not found.",
            )

        if reservation.waiter_id != waiter_id:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only the assigned waiter can create an order for this reservation.",
            )

        for item in request.items:
            if self._dish_repo.get(item.dish_id) is None:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                    f"Dish '{item.dish_id}' not found.",
                )

        order = Order(
            id=uuid4(),
            reservation_id=request.reservation_id,
            waiter_id=waiter_id,
            items=[
                OrderItem(dish_id=item.dish_id, quantity=item.quantity)
                for item in request.items
            ],
            created_at=datetime.now(UTC),
        )

        self._order_repo.create(order)
        logger.info("Order created", order_id=str(order.id))

        return CreateOrderResponse(
            orderId=str(order.id),
            reservationId=str(order.reservation_id),
        )

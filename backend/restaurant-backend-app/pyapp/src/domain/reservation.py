"""Domain model for a reservation persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel
from enums import ReservationStatus
from pydantic import AwareDatetime


class Reservation(DynamoModel):
    """Represents a reservation made by a customer or waiter.

    ``slot_ids`` holds every 90-minute slot booked under this reservation;
    a single-slot booking still uses a one-element list so the schema is
    uniform.

    For customer-created reservations:
        - customer_id is set, waiter_id is assigned (first available)
    For waiter-created reservations:
        - waiter_id is the creator, customer_id is set (existing customer)
          or null (visitor), and client_name holds the customer/visitor name.
    """

    _exclude_none = True

    id: UUID
    customer_id: UUID | None = None
    client_name: str | None = None
    waiter_id: UUID | None = None
    created_at: AwareDatetime
    slot_ids: list[UUID]
    status: ReservationStatus
    number_of_guests: int
    date: str | None = None

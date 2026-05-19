"""Domain model for a reservation persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel
from enums.reservation_status import ReservationStatus
from pydantic import AwareDatetime


class Reservation(DynamoModel):
    """Represents a reservation made by a customer.

    ``slot_ids`` holds every 90-minute slot booked under this reservation;
    a single-slot booking still uses a one-element list so the schema is
    uniform.
    """

    id: UUID
    customer_id: UUID | None
    waiter_id: UUID | None
    created_at: AwareDatetime
    slot_ids: list[UUID]
    status: ReservationStatus
    number_of_guests: int

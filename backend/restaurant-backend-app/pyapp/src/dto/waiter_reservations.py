"""DTOs for the GET /reservations/waiter table-view endpoint."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class GetWaiterReservationsRequest(BaseModel):
    """Required query parameters for the waiter table-view endpoint.

    Field names match the incoming query-string keys, so no aliases are needed.
    All three parameters are mandatory; a missing or malformed value surfaces as
    a 422 via the handler's ``_validate`` helper.

    ``date`` accepts any ISO 8601 date string (e.g. ``2024-06-15``); Pydantic
    parses and validates it as a :class:`datetime.date`.
    """

    model_config = ConfigDict(extra="ignore")

    date: date
    time_from: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    table_name: str = Field(..., min_length=1)


class ReservationWaiterViewDTO(BaseModel):
    """Single reservation as shown on the waiter table-view dashboard."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservation_id: str = Field(..., alias="reservationId")
    customer_id: str | None = Field(None, alias="customerId")
    created_by: str | None = Field(None, alias="createdBy")
    location_address: str | None = Field(None, alias="location_address")
    table_number: int | None = Field(None, alias="tableNumber")
    date: str
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")
    guests_number: int = Field(..., alias="guestsNumber")


class WaiterReservationListResponse(BaseModel):
    """Top-level wrapper for the waiter table-view reservation list."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservations: list[ReservationWaiterViewDTO]

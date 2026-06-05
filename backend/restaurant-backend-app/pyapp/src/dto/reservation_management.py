"""DTOs used by reservation dashboard and reservation lifecycle endpoints."""

from __future__ import annotations

from enums.reservation_status import ReservationStatus
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AllowedActions(BaseModel):
    """Frontend-ready flags for reservation action buttons."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    can_edit: bool = Field(..., alias="canEdit")
    can_cancel: bool = Field(..., alias="canCancel")


class ReservationView(BaseModel):
    """Reservation payload enriched with derived data for dashboards."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservation_id: str = Field(..., alias="reservationId")
    status: str
    customer_id: str | None = Field(None, alias="customerId")
    client_name: str | None = Field(None, alias="clientName")
    waiter_id: str | None = Field(None, alias="waiterId")
    location_id: str | None = Field(None, alias="locationId")
    location_address: str | None = Field(None, alias="location_address")
    table_number: int | None = Field(None, alias="tableNumber")
    date: str
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")
    guests_number: int = Field(..., alias="guestsNumber")
    allowed_actions: AllowedActions = Field(..., alias="allowedActions")
    cutoff_reason: str | None = Field(None, alias="cutoffReason")


class ReservationListResponse(BaseModel):
    """List wrapper for customer/waiter dashboard reservations."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservations: list[ReservationView]


class UpdateReservationRequest(BaseModel):
    """Editable reservation fields for customer/waiter actions."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    guests_number: int | None = Field(None, alias="guestsNumber", gt=0, le=10)
    status: ReservationStatus | None = None

    @model_validator(mode="after")
    def ensure_any_field_is_set(self) -> "UpdateReservationRequest":
        """Reject empty update payloads."""
        if self.guests_number is None and self.status is None:
            raise ValueError("At least one editable field must be provided")
        return self

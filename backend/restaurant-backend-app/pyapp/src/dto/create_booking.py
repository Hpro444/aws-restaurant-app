"""DTOs for the POST /bookings/client endpoint."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# ── Request DTO ───────────────────────────────────────────────────────


class CreateBookingRequest(BaseModel):
    """Validated request body for creating a customer reservation.

    The frontend sends camelCase keys (``locationId``, ``tableNumber``,
    etc.); aliases mirror those names while internal Python access uses
    snake_case.
    """

    model_config = ConfigDict(populate_by_name=True)

    location_id: UUID = Field(..., alias="locationId")
    table_number: int = Field(..., alias="tableNumber", gt=0)
    date: str
    guests_number: int = Field(..., alias="guestsNumber", gt=0, le=10)
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")

    @field_validator("table_number", mode="before")
    @classmethod
    def coerce_table_number(cls, v: object) -> object:
        """Allow numeric strings (e.g. ``"1"``) for ``tableNumber``."""
        if isinstance(v, str) and v.strip():
            try:
                return int(v)
            except ValueError as exc:
                raise ValueError("tableNumber must be an integer") from exc
        return v

    @field_validator("guests_number", mode="before")
    @classmethod
    def coerce_guests_number(cls, v: object) -> object:
        """Allow numeric strings (e.g. ``"4"``) for ``guestsNumber``."""
        if isinstance(v, str) and v.strip():
            try:
                return int(v)
            except ValueError as exc:
                raise ValueError("guestsNumber must be an integer") from exc
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Reject invalid format, past dates, and dates >30 days ahead."""
        if not v:
            raise ValueError("Date is required")
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Date must be in YYYY-MM-DD format") from exc

        today = date.today()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return v

    @field_validator("time_from", "time_to")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate that time fields are present and in HH:MM format."""
        if not v:
            raise ValueError("Time is required")
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError as exc:
            raise ValueError("Time must be in HH:MM format") from exc
        return v

    @field_validator("time_to")
    @classmethod
    def validate_time_window(cls, time_to: str, info: ValidationInfo) -> str:
        """Ensure ``timeTo`` is strictly greater than ``timeFrom``."""
        time_from = info.data.get("time_from")
        if time_from and time_to <= time_from:
            raise ValueError("timeTo must be greater than timeFrom")
        return time_to


# ── Response DTO ──────────────────────────────────────────────────────


class CreateBookingResponse(BaseModel):
    """Payload returned on a successful reservation for UI confirmation."""

    model_config = ConfigDict(populate_by_name=True)

    reservation_id: str = Field(..., alias="reservationId")
    status: str
    location_id: str = Field(..., alias="locationId")
    table_number: int = Field(..., alias="tableNumber")
    date: str
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")
    guests_number: int = Field(..., alias="guestsNumber")

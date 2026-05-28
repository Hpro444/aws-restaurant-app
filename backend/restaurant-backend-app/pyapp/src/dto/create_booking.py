"""DTOs for the POST /bookings/client endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# ── Request DTO ───────────────────────────────────────────────────────


class CreateBookingRequest(BaseModel):
    """Validated request body for creating a customer reservation.

    The frontend sends camelCase keys (``locationId``, ``tableNumber``,
    etc.); aliases mirror those names while internal Python access uses
    snake_case.
    """

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", str_strip_whitespace=True
    )

    location_id: UUID = Field(..., alias="locationId")
    table_number: int = Field(..., alias="tableNumber", gt=0)
    date: str = Field(..., min_length=1)
    guests_number: int = Field(..., alias="guestsNumber", gt=0, le=10)
    time_from: str = Field(..., alias="timeFrom", min_length=1)
    time_to: str = Field(..., alias="timeTo", min_length=1)

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

        today = datetime.now(timezone.utc).date()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return v

    @field_validator("time_from", "time_to")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """Validate that time fields are UTC ISO datetimes."""
        if not v:
            raise ValueError("Time is required")
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "Time must be a UTC ISO datetime (e.g. 2026-05-27T11:45:00Z)"
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("Time must be in UTC (offset +00:00 or Z)")

        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @field_validator("time_to")
    @classmethod
    def validate_time_window(cls, time_to: str, info: ValidationInfo) -> str:
        """Ensure ``timeTo`` is strictly greater than ``timeFrom``."""
        time_from = info.data.get("time_from")
        if time_from:
            parsed_from = datetime.fromisoformat(time_from.replace("Z", "+00:00"))
            parsed_to = datetime.fromisoformat(time_to.replace("Z", "+00:00"))
            if parsed_to <= parsed_from:
                raise ValueError("timeTo must be greater than timeFrom")
        return time_to


# ── Response DTO ──────────────────────────────────────────────────────


class CreateBookingResponse(BaseModel):
    """Payload returned on a successful reservation for UI confirmation."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    reservation_id: str = Field(..., alias="reservationId")
    status: str
    location_id: str = Field(..., alias="locationId")
    location_address: str = Field(..., alias="location_address")
    table_number: int = Field(..., alias="tableNumber")
    date: str
    time_from: str = Field(..., alias="timeFrom")
    time_to: str = Field(..., alias="timeTo")
    guests_number: int = Field(..., alias="guestsNumber")

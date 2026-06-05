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
    existing_customer: bool | None = Field(None, alias="existingCustomer")
    customer_id: UUID | None = Field(None, alias="customerId")
    client_name: str | None = Field(None, alias="clientName", min_length=1)
    time_from: str = Field(..., alias="timeFrom", min_length=1)
    time_to: str = Field(..., alias="timeTo", min_length=1)

    @staticmethod
    def _coerce_int(raw_value: object, field_name: str) -> object:
        """Allow numeric strings for integer request fields."""
        if isinstance(raw_value, str) and raw_value.strip():
            try:
                return int(raw_value)
            except ValueError as exc:
                raise ValueError(f"{field_name} must be an integer") from exc
        return raw_value

    @staticmethod
    def _parse_utc_datetime(raw_value: str) -> datetime:
        """Parse and normalize UTC ISO datetime values."""
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "Time must be a UTC ISO datetime (e.g. 2026-05-27T11:45:00Z)"
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("Time must be in UTC (offset +00:00 or Z)")
        return parsed.astimezone(timezone.utc)

    @field_validator("table_number", "guests_number", mode="before")
    @classmethod
    def coerce_int_fields(cls, raw_value: object, info: ValidationInfo) -> object:
        """Allow numeric strings for integer request fields."""
        field_name = (
            "tableNumber" if info.field_name == "table_number" else "guestsNumber"
        )
        return cls._coerce_int(raw_value, field_name)

    @field_validator("date")
    @classmethod
    def validate_date(cls, date_value: str) -> str:
        """Reject invalid format, past dates, and dates >30 days ahead."""
        if not date_value:
            raise ValueError("Date is required")
        try:
            parsed = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Date must be in YYYY-MM-DD format") from exc

        today = datetime.now(timezone.utc).date()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return date_value

    @field_validator("time_from", "time_to")
    @classmethod
    def validate_time(cls, time_value: str, info: ValidationInfo) -> str:
        """Validate that time fields are UTC ISO datetimes."""
        if not time_value:
            raise ValueError("Time is required")

        parsed = cls._parse_utc_datetime(time_value)
        requested_date = info.data.get("date")
        field_label = "timeFrom" if info.field_name == "time_from" else "timeTo"
        if requested_date and parsed.date().isoformat() != requested_date:
            raise ValueError(f"{field_label} date must match date")

        return parsed.isoformat().replace("+00:00", "Z")

    @field_validator("time_to")
    @classmethod
    def validate_time_window(cls, time_to: str, info: ValidationInfo) -> str:
        """Ensure ``timeTo`` is strictly greater than ``timeFrom``."""
        time_from = info.data.get("time_from")
        if time_from:
            parsed_from = cls._parse_utc_datetime(time_from)
            parsed_to = cls._parse_utc_datetime(time_to)
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
    client_name: str | None = Field(None, alias="clientName")

"""DTOs for the available-tables endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# ── Request DTO ───────────────────────────────────────────────────────


class AvailableTablesRequest(BaseModel):
    """Validated query parameters for table availability search.

    All three fields are mandatory. The ``location_id`` is validated
    as a valid UUID, ``date`` is ISO format with a bookable window,
    and ``guests_number`` is positive and ≤ 10.

    Optional ``from_time`` must be a UTC ISO datetime string
    (example: ``2026-05-27T11:45:00Z``). It is snapped to the first
    valid slot start >= that time and returns all free slots from
    that point onwards.

    """

    @staticmethod
    def _parse_utc_datetime(raw_value: str) -> datetime:
        """Parse and normalize UTC ISO datetime values."""
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "from_time must be a UTC ISO datetime (e.g. 2026-05-27T11:45:00Z)"
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("from_time must be in UTC (offset +00:00 or Z)")
        return parsed.astimezone(timezone.utc)

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    location_id: UUID = Field(...)
    date: str = Field(..., min_length=1)
    guests_number: int = Field(..., gt=0, le=10)
    from_time: Optional[str] = Field(None)

    @field_validator("date")
    @classmethod
    def validate_date(cls, date_value: str) -> str:
        """Reject invalid format, past dates, and dates >30 days ahead."""
        if not date_value:
            raise ValueError("Date is required")
        try:
            parsed = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

        today = datetime.now(timezone.utc).date()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return date_value

    @field_validator("from_time")
    @classmethod
    def validate_time(
        cls, from_time_value: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        """Validate optional UTC datetime parameter in ISO-8601 format."""
        if not from_time_value:
            return None

        parsed = cls._parse_utc_datetime(from_time_value)
        requested_date = info.data.get("date")
        if requested_date and parsed.date().isoformat() != requested_date:
            raise ValueError("from_time date must match date")

        return parsed.isoformat().replace("+00:00", "Z")


class WaiterAvailableTablesRequest(BaseModel):
    """Validated query parameters for the waiter table availability search."""

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_default=True,
    )

    location_id: UUID = Field(...)
    date: str | None = Field(None)
    guests_number: int = Field(..., gt=0, le=10)
    from_time: str = Field(...)
    to_time: str = Field(...)

    @field_validator("date", mode="before")
    @classmethod
    def default_date(cls, date_value: str | None) -> str:
        """Default to today's UTC date when date is omitted."""
        if date_value in (None, ""):
            return datetime.now(timezone.utc).date().isoformat()
        return date_value

    @field_validator("date")
    @classmethod
    def validate_date(cls, date_value: str) -> str:
        """Reject invalid format, past dates, and dates >30 days ahead."""
        if not date_value:
            raise ValueError("Date is required")
        try:
            parsed = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

        today = datetime.now(timezone.utc).date()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return date_value

    @field_validator("from_time", "to_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        """Validate UTC ISO datetime format and normalize it to trailing Z."""
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "Time must be a UTC ISO datetime (e.g. 2026-05-27T11:45:00Z)"
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("Time must be in UTC (offset +00:00 or Z)")

        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @field_validator("from_time", "to_time")
    @classmethod
    def validate_time_matches_date(cls, value: str, info: ValidationInfo) -> str:
        """Ensure UTC datetimes are on the requested booking date."""
        requested_date = info.data.get("date")
        if not requested_date:
            return value

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.date().isoformat() != requested_date:
            raise ValueError("Time date must match date")
        return value

    @field_validator("to_time")
    @classmethod
    def validate_time_range(cls, to_time_value: str, info: ValidationInfo) -> str:
        """Ensure from_time is earlier than to_time."""
        from_time_value = info.data.get("from_time")
        if not from_time_value:
            return to_time_value

        from_time_dt = datetime.fromisoformat(from_time_value.replace("Z", "+00:00"))
        to_time_dt = datetime.fromisoformat(to_time_value.replace("Z", "+00:00"))
        if from_time_dt >= to_time_dt:
            raise ValueError("from_time must be earlier than to_time")
        return to_time_value


# ── Response DTOs ─────────────────────────────────────────────────────


class SlotResponse(BaseModel):
    """One bookable time window displayed in the UI slot picker.

    ``slot_id`` is sent back by the frontend in POST /bookings
    to create a reservation.

    """

    model_config = ConfigDict(extra="ignore")

    slot_id: str
    start_time: str
    end_time: str


class TableAvailabilityResponse(BaseModel):
    """One table result card as shown in the booking UI."""

    model_config = ConfigDict(extra="ignore")

    table_id: str
    table_number: int
    capacity: int
    location_address: str | None = Field(None, alias="location_address")
    available_slots: list[SlotResponse]


class AvailableTablesResponse(BaseModel):
    """Top-level response returned by GET /bookings/tables."""

    model_config = ConfigDict(extra="ignore")

    tables: list[TableAvailabilityResponse]

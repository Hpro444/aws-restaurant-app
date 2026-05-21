"""DTOs for the GET /bookings/tables endpoint."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ── Request DTO ───────────────────────────────────────────────────────


class AvailableTablesRequest(BaseModel):
    """Validated query parameters for table availability search.

    All three fields are mandatory. The ``location_id`` is validated
    as a valid UUID, ``date`` is ISO format with a bookable window,
    and ``guests_number`` is positive and ≤ 10.

    Optional ``from_time`` snaps to the first valid slot start >= the
    entered time and returns all free slots from that point onwards.

    """

    location_id: UUID = Field(...)
    date: str
    guests_number: int = Field(..., gt=0, le=10)
    from_time: Optional[str] = Field(None)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Reject invalid format, past dates, and dates >30 days ahead."""
        if not v:
            raise ValueError("Date is required")
        try:
            parsed = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

        today = date.today()
        if parsed < today:
            raise ValueError("Cannot book a table in the past")
        if parsed > today + timedelta(days=30):
            raise ValueError("Cannot book more than 30 days in advance")

        return v

    @field_validator("from_time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        """Validate optional time parameter is in HH:MM format."""
        if v is None or v == "":
            return None
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        return v


# ── Response DTOs ─────────────────────────────────────────────────────


class SlotResponse(BaseModel):
    """One bookable time window displayed in the UI slot picker.

    ``slot_id`` is sent back by the frontend in POST /bookings
    to create a reservation.

    """

    slot_id: str
    start_time: str
    end_time: str


class TableAvailabilityResponse(BaseModel):
    """One table result card as shown in the booking UI."""

    table_id: str
    table_number: int
    capacity: int
    location_address: str | None = Field(None, alias="location_address")
    available_slots: list[SlotResponse]


class AvailableTablesResponse(BaseModel):
    """Top-level response returned by GET /bookings/tables."""

    tables: list[TableAvailabilityResponse]

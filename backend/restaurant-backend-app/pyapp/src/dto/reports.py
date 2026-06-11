"""DTOs for admin reporting endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from commons.report_utils import parse_date, period_end_for, period_start_for
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class ReportType(str, Enum):
    """Supported report categories in the reporting dashboard."""

    STAFF_PERFORMANCE = "staff_performance"
    SALES = "sales"


class GetReportsRequest(BaseModel):
    """Query params accepted by GET /reports."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    report_type: str | ReportType = Field(
        ReportType.STAFF_PERFORMANCE,
        alias="reportType",
    )
    period: str | None = None
    period_start: str | None = Field(None, alias="periodStart")
    period_end: str | None = Field(None, alias="periodEnd")
    location_id: UUID | None = Field(None, alias="locationId")

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "GetReportsRequest":
        """Normalize report type and ensure period range can be resolved."""
        if isinstance(self.report_type, str):
            raw = self.report_type.strip().lower().replace(" ", "_")
            if raw in {"staff", "staffperformance", "staff_performance"}:
                self.report_type = ReportType.STAFF_PERFORMANCE
            elif raw in {"sales", "location", "location_comparison"}:
                self.report_type = ReportType.SALES
            else:
                raise ValueError(
                    "'reportType' must be one of: staff_performance, sales"
                )

        # Validate at parse time so handler returns 422 for bad period input.
        _ = self.resolve_period_range()
        return self

    def resolve_period_range(self) -> tuple[date, date]:
        """Resolve requested period to a validated start/end date tuple."""
        start_value = self.period_start
        end_value = self.period_end

        if self.period:
            value = self.period.strip()
            if " - " in value:
                period_start_raw, period_end_raw = value.split(" - ", 1)
                start_value = start_value or period_start_raw.strip()
                end_value = end_value or period_end_raw.strip()
            else:
                start_value = start_value or value

        if not start_value:
            raise ValueError("'periodStart' or 'period' is required")

        start_date = parse_date(start_value)
        end_date = parse_date(end_value) if end_value else period_end_for(start_date)
        if end_date < start_date:
            raise ValueError(
                "'periodEnd' must be greater than or equal to 'periodStart'"
            )

        today = datetime.now(UTC).date()
        if start_date > today:
            raise ValueError("'periodStart' must not be in the future")
        if end_date > today:
            raise ValueError("'periodEnd' must not be in the future")

        return start_date, end_date

    def resolve_period_start(self) -> date:
        """Resolve requested period start to the ISO-week Monday used by report rows."""
        start_date, _ = self.resolve_period_range()
        return period_start_for(start_date)


class ReportsResponse(BaseModel):
    """Table payload returned by GET /reports."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    report_type: ReportType = Field(..., alias="reportType")
    period_start: str = Field(..., alias="periodStart")
    period_end: str = Field(..., alias="periodEnd")
    rows: list[dict[str, Any]]


class DownloadFormat(str, Enum):
    """Supported file formats for report downloads."""

    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class CreateReportsDownloadRequest(BaseModel):
    """Combined request for POST /reports/download.

    The file format is supplied as a query-string parameter (``fileFormat``)
    or legacy key (``format``);
    the rest of the report payload is supplied in the JSON request body.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    report_type: ReportType = Field(..., alias="reportType")
    period_start: str = Field(..., alias="periodStart")
    period_end: str = Field(..., alias="periodEnd")
    rows: list[dict[str, Any]] = Field(default_factory=list)
    download_format: DownloadFormat = Field(
        DownloadFormat.PDF,
        alias="fileFormat",
        validation_alias=AliasChoices("fileFormat", "format"),
    )

    @model_validator(mode="after")
    def validate_period(self) -> "CreateReportsDownloadRequest":
        """Validate that period dates are parseable and in the right order."""
        start_date = parse_date(self.period_start)
        end_date = parse_date(self.period_end)
        if end_date < start_date:
            raise ValueError(
                "'periodEnd' must be greater than or equal to 'periodStart'"
            )
        return self

"""Domain model for the weekly location comparison report persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class LocationReport(DynamoModel):
    """Weekly comparison report for a single restaurant location.

    One row exists per (location, ISO-week) pair. The ``location_period_index``
    GSI supports queries by location and period; the primary key ``id`` is a
    ``uuid4`` assigned on first creation.
    """

    id: UUID
    location_id: UUID
    location_name: str
    report_period_start: str
    report_period_end: str
    orders_processed: int
    orders_processed_delta_pct: float | None = None
    cuisine_feedback_count: int
    cuisine_feedback_sum: float
    avg_cuisine_feedback: float | None = None
    min_cuisine_feedback: int | None = None
    avg_cuisine_feedback_delta_pct: float | None = None
    revenue: float = 0.0
    revenue_delta_pct: float | None = None

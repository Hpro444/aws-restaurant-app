"""Domain model for the weekly waiter performance report persisted in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.dynamo_model import DynamoModel


class WaiterReport(DynamoModel):
    """Weekly performance report for a single waiter.

    One row exists per (waiter, ISO-week) pair. The ``waiter_period_index`` GSI
    supports queries by waiter and period; the primary key ``id`` is a ``uuid4``
    assigned on first creation.
    """

    id: UUID
    waiter_id: UUID
    location_id: UUID
    location_name: str
    waiter_first_name: str
    waiter_last_name: str
    waiter_email: str
    report_period_start: str
    report_period_end: str
    working_hours: float
    orders_processed: int
    service_feedback_count: int
    service_feedback_sum: float
    avg_service_feedback: float | None = None
    min_service_feedback: int | None = None
    orders_processed_delta_pct: float | None = None
    avg_service_feedback_delta_pct: float | None = None

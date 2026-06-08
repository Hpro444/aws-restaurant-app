"""Denormalized read model backing the waiter table-view dashboard."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commons.dynamo_model import DynamoModel
from enums import ReservationStatus


class ReservationWaiterView(DynamoModel):
    """Flattened projection of a reservation for the waiter dashboard.

    One row exists per reservation, keyed by ``id`` (the reservation id) so the
    generic :class:`DynamoRepository` CRUD applies directly. The
    ``location_date_index`` GSI answers the "by location, date, start time and
    table" query in a single call; its key attributes ``location_date`` and
    ``time_table`` are synthesized in :meth:`to_dynamodb_item` rather than stored
    as model fields.
    """

    id: UUID
    customer_id: UUID | None
    created_by: str | None = None
    waiter_id: UUID | None
    location_id: UUID
    location_address: str | None
    table_number: int | None
    table_name: str
    date: str
    time_from: str
    time_to: str
    guests_number: int
    status: ReservationStatus

    @staticmethod
    def location_date(location_id: UUID | str, date: str) -> str:
        """Build the ``location_date_index`` partition value (``location_id#date``)."""
        return f"{location_id}#{date}"

    @staticmethod
    def time_table(time_from: str, table_name: str) -> str:
        """Build the ``location_date_index`` sort value (``time_from#table_name``)."""
        return f"{time_from}#{table_name}"

    def to_dynamodb_item(self) -> dict[str, Any]:
        """Serialize to a DynamoDB item, injecting the GSI key attributes."""
        item = super().to_dynamodb_item()
        item["location_date"] = {"S": self.location_date(self.location_id, self.date)}
        item["time_table"] = {"S": self.time_table(self.time_from, self.table_name)}
        return item

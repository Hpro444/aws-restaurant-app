"""Repository for ReservationWaiterView projection rows in DynamoDB."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.reservation_waiter_view import ReservationWaiterView

from repositories.base_repository import DynamoRepository


class ReservationWaiterViewRepository(DynamoRepository[ReservationWaiterView]):
    """CRUD for the waiter-dashboard projection plus a date/time/table query.

    The table is keyed on ``id`` (the reservation id), so the inherited
    ``create`` / ``update`` / ``delete`` are reused as-is for projection writes
    and deletes. Only the GSI-backed read needs a dedicated method.
    """

    _LOCATION_DATE_INDEX = "location_date_index"

    def __init__(self, settings: AppConfig | None = None) -> None:
        """Initialise with the reservation-waiter-view table alias from AppConfig.

        Args:
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        super().__init__(cfg.reservation_waiter_view_table, ReservationWaiterView, cfg)

    def query_for_table(
        self,
        location_id: UUID,
        date: str,
        time_from: str,
        table_name: str,
        waiter_id: UUID,
    ) -> list[ReservationWaiterView]:
        """Return projected reservations for one location/date/start-time/table assigned to a waiter.

        Uses the ``location_date_index`` GSI where:
        - Partition key = ``location_date`` (``location_id#date``)
        - Sort key = ``time_table`` (``time_from#table_name``)

        A ``FilterExpression`` on ``waiter_id`` ensures only rows assigned to the
        requesting waiter are returned.

        Args:
            location_id: UUID of the location the waiter is assigned to.
            date: Booking date as a ``YYYY-MM-DD`` string.
            time_from: Start time as an ``HH:MM`` string.
            table_name: Table identifier (string form of the table number).
            waiter_id: UUID of the waiter making the request.

        Returns:
            List of matching :class:`ReservationWaiterView` rows assigned to the waiter.

        """
        items = self._paginated_query(
            "location_date_index query",
            self._client.query,
            TableName=self._resolve_table_name(),
            IndexName=self._LOCATION_DATE_INDEX,
            KeyConditionExpression="location_date = :pk AND time_table = :tt",
            FilterExpression="#wid = :wid",
            ExpressionAttributeNames={"#wid": "waiter_id"},
            ExpressionAttributeValues={
                ":pk": {"S": ReservationWaiterView.location_date(location_id, date)},
                ":tt": {"S": ReservationWaiterView.time_table(time_from, table_name)},
                ":wid": {"S": str(waiter_id)},
            },
        )

        logger.info(
            "Waiter-view reservations queried",
            location_id=str(location_id),
            date=date,
            time_from=time_from,
            table_name=table_name,
            waiter_id=str(waiter_id),
            count=len(items),
        )
        return items

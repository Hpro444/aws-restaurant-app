"""Tests for ReservationWaiterViewRepository GSI query and reused base CRUD."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.reservation_waiter_view import (  # type: ignore[import-untyped]
        ReservationWaiterView,
    )
    from enums import ReservationStatus  # type: ignore[import-untyped]
    from repositories.reservation_waiter_view_repository import (  # type: ignore[import-untyped]
        ReservationWaiterViewRepository,
    )

_RES_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_LOC_ID = uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
_WAITER_ID = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
_DATE = "2026-05-16"


def _make_view() -> ReservationWaiterView:
    """Build a representative projection row for tests."""
    return ReservationWaiterView(
        id=_RES_ID,
        customer_id=None,
        waiter_id=None,
        location_id=_LOC_ID,
        location_address="1 Freedom Square, Tbilisi",
        table_number=5,
        table_name="5",
        date=_DATE,
        time_from="12:00",
        time_to="13:30",
        guests_number=4,
        status=ReservationStatus.RESERVED,
    )


class _RepoTestCase(unittest.TestCase):
    """Base class with mocked boto3 client and resolved table name."""

    def setUp(self) -> None:
        """Patch boto3, create repository, and bypass table-name resolution."""
        patcher = patch("repositories.base_repository.boto3")
        self.mock_boto3 = patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.addCleanup(patcher.stop)

        self.repo = ReservationWaiterViewRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-waiter-view")


class TestQueryForTable(_RepoTestCase):
    """Tests for ReservationWaiterViewRepository.query_for_table."""

    def test_targets_gsi_with_exact_key_condition(self) -> None:
        """Query must target location_date_index with an exact PK+SK condition and waiter filter."""
        self.mock_client.query.return_value = {"Items": []}

        self.repo.query_for_table(_LOC_ID, _DATE, "12:00", "5", waiter_id=_WAITER_ID)

        kwargs = self.mock_client.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "location_date_index")
        self.assertEqual(
            kwargs["KeyConditionExpression"],
            "location_date = :pk AND time_table = :tt",
        )
        self.assertEqual(kwargs["FilterExpression"], "#wid = :wid")
        self.assertEqual(kwargs["ExpressionAttributeNames"], {"#wid": "waiter_id"})
        self.assertEqual(
            kwargs["ExpressionAttributeValues"],
            {
                ":pk": {"S": f"{_LOC_ID}#{_DATE}"},
                ":tt": {"S": "12:00#5"},
                ":wid": {"S": str(_WAITER_ID)},
            },
        )

    def test_deserializes_returned_items(self) -> None:
        """Returned items must be deserialized into ReservationWaiterView models."""
        self.mock_client.query.return_value = {
            "Items": [_make_view().to_dynamodb_item()]
        }

        result = self.repo.query_for_table(
            _LOC_ID, _DATE, "12:00", "5", waiter_id=_WAITER_ID
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, _RES_ID)
        self.assertEqual(result[0].table_number, 5)


class TestReusedBaseCrud(_RepoTestCase):
    """Tests that base DynamoRepository CRUD works against the id-keyed table."""

    def test_create_puts_item_with_id_guard_and_gsi_attrs(self) -> None:
        """Create must conditionally put an item carrying the synthesized GSI attrs."""
        self.mock_client.put_item.return_value = {}

        self.repo.create(_make_view())

        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertEqual(kwargs["ConditionExpression"], "attribute_not_exists(id)")
        self.assertEqual(kwargs["Item"]["id"], {"S": str(_RES_ID)})
        self.assertEqual(kwargs["Item"]["location_date"], {"S": f"{_LOC_ID}#{_DATE}"})
        self.assertEqual(kwargs["Item"]["time_table"], {"S": "12:00#5"})

    def test_update_puts_item_without_condition(self) -> None:
        """Update must put the item as an unconditional upsert."""
        self.mock_client.put_item.return_value = {}

        self.repo.update(_make_view())

        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertNotIn("ConditionExpression", kwargs)
        self.assertEqual(kwargs["Item"]["id"], {"S": str(_RES_ID)})

    def test_delete_keys_on_id(self) -> None:
        """Delete must remove the row by its id partition key."""
        self.repo.delete(_RES_ID)

        kwargs = self.mock_client.delete_item.call_args.kwargs
        self.assertEqual(kwargs["Key"], {"id": {"S": str(_RES_ID)}})


if __name__ == "__main__":
    unittest.main()

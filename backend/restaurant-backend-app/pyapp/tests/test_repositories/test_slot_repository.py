"""Tests for SlotRepository table+date DynamoDB query methods."""

import unittest
import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.slot import Slot  # type: ignore[import-untyped]
    from enums import SlotStatus  # type: ignore[import-untyped]
    from repositories.slot_repository import (
        SlotRepository,  # type: ignore[import-untyped]
    )

_TABLE_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TABLE_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_SLOT_1_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_SLOT_2_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_DATE = date(2026, 5, 16)
_DATE_ISO = _DATE.isoformat()


def _aware(h: int, m: int) -> datetime:
    """Return an aware datetime for test slots."""
    return datetime(2026, 5, 16, h, m, tzinfo=timezone.utc)


def _slot(slot_id: uuid.UUID, table_id: uuid.UUID, h: int, m: int) -> Slot:
    """Build a Slot domain model for tests."""
    start = _aware(h, m)
    end = _aware(h + 1, (m + 30) % 60)
    return Slot(
        id=slot_id,
        table_id=table_id,
        start_time=start,
        end_time=end,
        date=_aware(0, 0),
    )


_SLOT_1 = _slot(_SLOT_1_ID, _TABLE_1_ID, 10, 0)
_SLOT_2 = _slot(_SLOT_2_ID, _TABLE_1_ID, 12, 0)

_GENERIC_CLIENT_ERROR = ClientError(
    {"Error": {"Code": "InternalServerError", "Message": "oops"}},
    "Query",
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

        self.repo = SlotRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-slots")


class TestFindByTableIdAndDate(_RepoTestCase):
    """Tests for SlotRepository.find_by_table_id_and_date."""

    def test_returns_slots_from_single_query_page(self) -> None:
        """A single query page must deserialize into Slot models."""
        self.mock_client.query.return_value = {
            "Items": [_SLOT_1.to_dynamodb_item(), _SLOT_2.to_dynamodb_item()]
        }

        result = self.repo.find_by_table_id_and_date(_TABLE_1_ID, _DATE)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, _SLOT_1_ID)

    def test_paginates_until_last_page(self) -> None:
        """Must follow LastEvaluatedKey and merge all query pages."""
        self.mock_client.query.side_effect = [
            {
                "Items": [_SLOT_1.to_dynamodb_item()],
                "LastEvaluatedKey": {"id": {"S": str(_SLOT_1_ID)}},
            },
            {"Items": [_SLOT_2.to_dynamodb_item()]},
        ]

        result = self.repo.find_by_table_id_and_date(_TABLE_1_ID, _DATE)

        self.assertEqual(len(result), 2)
        self.assertEqual(self.mock_client.query.call_count, 2)

    def test_returns_empty_list_on_client_error(self) -> None:
        """A DynamoDB ClientError must return an empty list without raising."""
        self.mock_client.query.side_effect = _GENERIC_CLIENT_ERROR

        self.assertEqual(self.repo.find_by_table_id_and_date(_TABLE_1_ID, _DATE), [])

    def test_uses_table_date_index_and_begins_with_expression(self) -> None:
        """Query must target table_id-date-index with begins_with on date."""
        self.mock_client.query.return_value = {"Items": []}

        self.repo.find_by_table_id_and_date(_TABLE_1_ID, _DATE)

        kwargs = self.mock_client.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "table_id_date_index")
        self.assertIn("begins_with(#d, :date_prefix)", kwargs["KeyConditionExpression"])
        self.assertEqual(kwargs["ExpressionAttributeNames"], {"#d": "date"})
        self.assertEqual(
            kwargs["ExpressionAttributeValues"],
            {":tid": {"S": str(_TABLE_1_ID)}, ":date_prefix": {"S": _DATE_ISO}},
        )


class TestFindByTableIdsAndDate(_RepoTestCase):
    """Tests for SlotRepository.find_by_table_ids_and_date."""

    def test_combines_results_from_each_table_id(self) -> None:
        """Must call per-table query method and concatenate all slot results."""
        slot_for_table_2 = _slot(
            uuid.UUID("55555555-5555-5555-5555-555555555555"),
            _TABLE_2_ID,
            14,
            0,
        )
        self.repo.find_by_table_id_and_date = MagicMock(
            side_effect=[[_SLOT_1, _SLOT_2], [slot_for_table_2]]
        )

        result = self.repo.find_by_table_ids_and_date({_TABLE_1_ID, _TABLE_2_ID}, _DATE)

        self.assertEqual(len(result), 3)
        self.assertEqual(self.repo.find_by_table_id_and_date.call_count, 2)


_CONDITIONAL_CHECK_FAILED = ClientError(
    {"Error": {"Code": "ConditionalCheckFailedException", "Message": "state changed"}},
    "UpdateItem",
)


class TestUpdateStatus(_RepoTestCase):
    """Tests for SlotRepository.update_status conditional transitions."""

    def test_returns_true_on_successful_conditional_update(self) -> None:
        """A clean update_item call must yield True and target the status attribute."""
        self.mock_client.update_item.return_value = {}

        ok = self.repo.update_status(
            _SLOT_1_ID,
            new_status=SlotStatus.RESERVED,
            expected=SlotStatus.FREE,
        )

        self.assertTrue(ok)
        kwargs = self.mock_client.update_item.call_args.kwargs
        self.assertEqual(kwargs["TableName"], "test-slots")
        self.assertEqual(kwargs["Key"], {"id": {"S": str(_SLOT_1_ID)}})
        self.assertEqual(kwargs["UpdateExpression"], "SET #s = :new")
        self.assertEqual(kwargs["ConditionExpression"], "#s = :expected")
        self.assertEqual(kwargs["ExpressionAttributeNames"], {"#s": "status"})
        self.assertEqual(
            kwargs["ExpressionAttributeValues"],
            {":new": {"S": "RESERVED"}, ":expected": {"S": "FREE"}},
        )

    def test_returns_false_when_condition_fails(self) -> None:
        """ConditionalCheckFailedException must yield False without raising."""
        self.mock_client.update_item.side_effect = _CONDITIONAL_CHECK_FAILED

        ok = self.repo.update_status(
            _SLOT_1_ID,
            new_status=SlotStatus.RESERVED,
            expected=SlotStatus.FREE,
        )

        self.assertFalse(ok)

    def test_returns_false_on_generic_client_error(self) -> None:
        """Other ClientErrors must yield False without raising."""
        self.mock_client.update_item.side_effect = _GENERIC_CLIENT_ERROR

        ok = self.repo.update_status(
            _SLOT_1_ID,
            new_status=SlotStatus.RESERVED,
            expected=SlotStatus.FREE,
        )

        self.assertFalse(ok)

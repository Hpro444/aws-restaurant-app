"""Tests for TableRepository location-based DynamoDB queries."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from domain.table import Table  # type: ignore[import-untyped]
    from repositories.table_repository import (
        TableRepository,  # type: ignore[import-untyped]
    )

_LOCATION_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TABLE_1_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_TABLE_2_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

_TABLE_1 = Table(id=_TABLE_1_ID, table_number=1, capacity=4, location_id=_LOCATION_ID)
_TABLE_2 = Table(id=_TABLE_2_ID, table_number=2, capacity=6, location_id=_LOCATION_ID)

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

        self.repo = TableRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-tables")


class TestFindByLocationId(_RepoTestCase):
    """Tests for TableRepository.find_by_location_id."""

    def test_returns_tables_from_single_query_page(self) -> None:
        """A single query page must deserialize into Table models."""
        self.mock_client.query.return_value = {
            "Items": [_TABLE_1.to_dynamodb_item(), _TABLE_2.to_dynamodb_item()]
        }

        result = self.repo.find_by_location_id(_LOCATION_ID)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, _TABLE_1_ID)
        self.assertEqual(result[1].id, _TABLE_2_ID)

    def test_paginates_until_last_page(self) -> None:
        """Must follow LastEvaluatedKey and combine all result pages."""
        self.mock_client.query.side_effect = [
            {
                "Items": [_TABLE_1.to_dynamodb_item()],
                "LastEvaluatedKey": {"id": {"S": str(_TABLE_1_ID)}},
            },
            {"Items": [_TABLE_2.to_dynamodb_item()]},
        ]

        result = self.repo.find_by_location_id(_LOCATION_ID)

        self.assertEqual(len(result), 2)
        self.assertEqual(self.mock_client.query.call_count, 2)

    def test_returns_empty_list_on_client_error(self) -> None:
        """A DynamoDB ClientError must return an empty list without raising."""
        self.mock_client.query.side_effect = _GENERIC_CLIENT_ERROR

        self.assertEqual(self.repo.find_by_location_id(_LOCATION_ID), [])

    def test_uses_location_index_and_partition_key(self) -> None:
        """Query must target location_id-index with location_id partition key."""
        self.mock_client.query.return_value = {"Items": []}

        self.repo.find_by_location_id(_LOCATION_ID)

        kwargs = self.mock_client.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "location_id_index")
        self.assertEqual(kwargs["KeyConditionExpression"], "location_id = :lid")
        self.assertEqual(
            kwargs["ExpressionAttributeValues"], {":lid": {"S": str(_LOCATION_ID)}}
        )

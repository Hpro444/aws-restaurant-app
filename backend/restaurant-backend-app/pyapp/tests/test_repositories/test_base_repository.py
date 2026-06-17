"""Tests for DynamoRepository CRUD operations using DishRepository as the concrete subject."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException  # type: ignore[import-untyped]
    from domain.dish import Dish  # type: ignore[import-untyped]
    from repositories.dish_repository import (
        DishRepository,  # type: ignore[import-untyped]
    )

_DISH_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_LOCATION_ID = uuid.UUID("87654321-4321-8765-4321-876543218765")

_DISH = Dish(
    id=_DISH_ID,
    location_id=_LOCATION_ID,
    name="Margherita",
    description="Classic pizza",
    image_url="https://example.com/pizza.jpg",
    price=12.99,
    weight_gram=350,
    specialty=False,
    popular=True,
)

_CONDITIONAL_CHECK_FAILED = ClientError(
    {"Error": {"Code": "ConditionalCheckFailedException", "Message": "exists"}},
    "PutItem",
)

_GENERIC_CLIENT_ERROR = ClientError(
    {"Error": {"Code": "InternalServerError", "Message": "oops"}},
    "PutItem",
)


class _DishRepoTestCase(unittest.TestCase):
    """Base class that wires up a mocked boto3 client and a DishRepository."""

    def setUp(self) -> None:
        """Patch boto3, create repository, and bypass table-name resolution."""
        patcher = patch("repositories.base_repository.boto3")
        self.mock_boto3 = patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.addCleanup(patcher.stop)
        self.repo = DishRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-dishes")


class TestResolveTableName(unittest.TestCase):
    """Tests for _resolve_table_name alias resolution and caching."""

    def setUp(self) -> None:
        """Set up a fresh repository with a mocked boto3 client."""
        patcher = patch("repositories.base_repository.boto3")
        self.mock_boto3 = patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.addCleanup(patcher.stop)
        self.repo = DishRepository()

    def test_returns_matching_table_name(self) -> None:
        """Must return the first table name that contains the alias."""
        self.mock_client.list_tables.return_value = {"TableNames": ["tm3-dishes-dev"]}
        self.assertEqual(self.repo._resolve_table_name(), "tm3-dishes-dev")

    def test_caches_resolved_name(self) -> None:
        """list_tables must be called only once across multiple resolve calls."""
        self.mock_client.list_tables.return_value = {"TableNames": ["tm3-dishes-dev"]}
        self.repo._resolve_table_name()
        self.repo._resolve_table_name()
        self.mock_client.list_tables.assert_called_once()

    def test_falls_back_to_alias_when_no_match(self) -> None:
        """Must return the raw alias when no table name contains it."""
        self.mock_client.list_tables.return_value = {"TableNames": ["other-table"]}
        self.assertEqual(self.repo._resolve_table_name(), "dishes")

    def test_paginates_until_match_found(self) -> None:
        """Must follow LastEvaluatedTableName pagination to find a matching table."""
        self.mock_client.list_tables.side_effect = [
            {"TableNames": ["unrelated"], "LastEvaluatedTableName": "unrelated"},
            {"TableNames": ["tm3-dishes-prod"]},
        ]
        self.assertEqual(self.repo._resolve_table_name(), "tm3-dishes-prod")
        self.assertEqual(self.mock_client.list_tables.call_count, 2)


class TestCreate(_DishRepoTestCase):
    """Tests for DynamoRepository.create."""

    def test_calls_put_item_with_condition_expression(self) -> None:
        """Create must call put_item with attribute_not_exists(id) condition."""
        self.repo.create(_DISH)
        self.mock_client.put_item.assert_called_once()
        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertEqual(kwargs["ConditionExpression"], "attribute_not_exists(id)")

    def test_item_serialized_into_put_call(self) -> None:
        """Create must pass the model's DynamoDB item as Item."""
        self.repo.create(_DISH)
        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertEqual(kwargs["Item"]["id"], {"S": str(_DISH_ID)})

    def test_raises_409_on_conditional_check_failed(self) -> None:
        """Create must raise ApplicationException(409) when the item already exists."""
        self.mock_client.put_item.side_effect = _CONDITIONAL_CHECK_FAILED
        with self.assertRaises(ApplicationException) as ctx:
            self.repo.create(_DISH)
        self.assertEqual(ctx.exception.code, 409)

    def test_swallows_other_client_errors(self) -> None:
        """Non-conflict ClientErrors must raise ApplicationException(500)."""
        self.mock_client.put_item.side_effect = _GENERIC_CLIENT_ERROR
        with self.assertRaises(ApplicationException) as ctx:
            self.repo.create(_DISH)
        self.assertEqual(ctx.exception.code, 500)


class TestGet(_DishRepoTestCase):
    """Tests for DynamoRepository.get."""

    def test_returns_model_when_item_found(self) -> None:
        """Get must deserialize and return the domain model when the item exists."""
        self.mock_client.get_item.return_value = {"Item": _DISH.to_dynamodb_item()}
        result = self.repo.get(_DISH_ID)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, _DISH_ID)

    def test_returns_none_when_item_missing(self) -> None:
        """Get must return None when DynamoDB returns no Item."""
        self.mock_client.get_item.return_value = {}
        self.assertIsNone(self.repo.get(_DISH_ID))

    def test_returns_none_on_client_error(self) -> None:
        """Get must return None without raising when a ClientError occurs."""
        self.mock_client.get_item.side_effect = _GENERIC_CLIENT_ERROR
        self.assertIsNone(self.repo.get(_DISH_ID))

    def test_uses_pk_field_in_key(self) -> None:
        """Get must pass the UUID as the id key in the DynamoDB request."""
        self.mock_client.get_item.return_value = {}
        self.repo.get(_DISH_ID)
        kwargs = self.mock_client.get_item.call_args.kwargs
        self.assertEqual(kwargs["Key"], {"id": {"S": str(_DISH_ID)}})


class TestUpdate(_DishRepoTestCase):
    """Tests for DynamoRepository.update."""

    def test_calls_put_item_without_condition(self) -> None:
        """Update must call put_item with no ConditionExpression."""
        self.repo.update(_DISH)
        self.mock_client.put_item.assert_called_once()
        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertNotIn("ConditionExpression", kwargs)

    def test_item_serialized_into_put_call(self) -> None:
        """Update must pass the model's DynamoDB item as Item."""
        self.repo.update(_DISH)
        kwargs = self.mock_client.put_item.call_args.kwargs
        self.assertEqual(kwargs["Item"]["name"], {"S": "Margherita"})


class TestDelete(_DishRepoTestCase):
    """Tests for DynamoRepository.delete."""

    def test_calls_delete_item_with_correct_key(self) -> None:
        """Delete must call delete_item with the UUID as the id key."""
        self.repo.delete(_DISH_ID)
        self.mock_client.delete_item.assert_called_once()
        kwargs = self.mock_client.delete_item.call_args.kwargs
        self.assertEqual(kwargs["Key"], {"id": {"S": str(_DISH_ID)}})

    def test_swallows_client_error(self) -> None:
        """Delete must not raise on ClientError."""
        self.mock_client.delete_item.side_effect = _GENERIC_CLIENT_ERROR
        self.repo.delete(_DISH_ID)  # must not raise


class TestScan(_DishRepoTestCase):
    """Tests for DynamoRepository.scan."""

    def test_returns_all_items_from_single_page(self) -> None:
        """Scan must deserialize and return all items when there is one page."""
        self.mock_client.scan.return_value = {"Items": [_DISH.to_dynamodb_item()]}
        results = self.repo.scan()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, _DISH_ID)

    def test_paginates_on_last_evaluated_key(self) -> None:
        """Scan must follow LastEvaluatedKey and combine items from all pages."""
        page1_item = _DISH.to_dynamodb_item()
        page2_dish = Dish(
            id=uuid.UUID("99999999-9999-9999-9999-999999999999"),
            location_id=_LOCATION_ID,
            name="Calzone",
            description="Folded pizza",
            image_url="https://example.com/calzone.jpg",
            price=13.50,
            weight_gram=400,
            specialty=True,
            popular=False,
        )
        page2_item = page2_dish.to_dynamodb_item()
        self.mock_client.scan.side_effect = [
            {"Items": [page1_item], "LastEvaluatedKey": {"id": {"S": str(_DISH_ID)}}},
            {"Items": [page2_item]},
        ]
        results = self.repo.scan()
        self.assertEqual(len(results), 2)
        ids = {r.id for r in results}
        self.assertIn(_DISH_ID, ids)
        self.assertIn(page2_dish.id, ids)

    def test_returns_empty_list_on_client_error(self) -> None:
        """Scan must return an empty list without raising on ClientError."""
        self.mock_client.scan.side_effect = _GENERIC_CLIENT_ERROR
        self.assertEqual(self.repo.scan(), [])


class TestPkFieldOverride(unittest.TestCase):
    """Tests verifying concrete repos expose the correct _pk_field."""

    def setUp(self) -> None:
        """Patch boto3 so no real AWS call is made during construction."""
        patcher = patch("repositories.base_repository.boto3")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dish_repo_uses_id_as_pk(self) -> None:
        """DishRepository must use 'id' as the primary key field."""
        self.assertEqual(DishRepository._pk_field, "id")

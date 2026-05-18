"""Tests for LoginAttemptsRepository domain-specific DynamoDB operations."""

import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from repositories.login_attempts_repository import (
        LoginAttemptsRepository,  # type: ignore[import-untyped]
    )

_EMAIL = "jane@example.com"
_LOCKOUT_TS = 9_999_999_999

_GENERIC_CLIENT_ERROR = ClientError(
    {"Error": {"Code": "InternalServerError", "Message": "oops"}},
    "Operation",
)


class _RepoTestCase(unittest.TestCase):
    """Base class: mocked boto3 client + LoginAttemptsRepository with resolved table."""

    def setUp(self) -> None:
        """Patch boto3, create repository, and bypass table-name resolution."""
        patcher = patch("repositories.base_repository.boto3")
        self.mock_boto3 = patcher.start()
        self.mock_client = MagicMock()
        self.mock_boto3.client.return_value = self.mock_client
        self.addCleanup(patcher.stop)
        self.repo = LoginAttemptsRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-login-attempts")


class TestPkField(unittest.TestCase):
    """Tests verifying LoginAttemptsRepository uses email as primary key."""

    def test_pk_field_is_email(self) -> None:
        """LoginAttemptsRepository must override _pk_field to 'email'."""
        self.assertEqual(LoginAttemptsRepository._pk_field, "email")


class TestGetLockoutUntil(_RepoTestCase):
    """Tests for LoginAttemptsRepository.get_lockout_until."""

    def test_returns_timestamp_when_lockout_field_present(self) -> None:
        """Must return the int value of lockout_until when the field exists."""
        self.mock_client.get_item.return_value = {
            "Item": {"lockout_until": {"N": str(_LOCKOUT_TS)}}
        }
        result = self.repo.get_lockout_until(_EMAIL)
        self.assertEqual(result, _LOCKOUT_TS)

    def test_returns_none_when_item_has_no_lockout_field(self) -> None:
        """Must return None when the item exists but lockout_until is absent."""
        self.mock_client.get_item.return_value = {"Item": {}}
        self.assertIsNone(self.repo.get_lockout_until(_EMAIL))

    def test_returns_none_when_item_does_not_exist(self) -> None:
        """Must return None when DynamoDB returns no Item at all."""
        self.mock_client.get_item.return_value = {}
        self.assertIsNone(self.repo.get_lockout_until(_EMAIL))

    def test_returns_none_on_client_error(self) -> None:
        """Must return None without raising when a ClientError occurs."""
        self.mock_client.get_item.side_effect = _GENERIC_CLIENT_ERROR
        self.assertIsNone(self.repo.get_lockout_until(_EMAIL))

    def test_uses_projection_expression(self) -> None:
        """Must include ProjectionExpression to fetch only the lockout field."""
        self.mock_client.get_item.return_value = {}
        self.repo.get_lockout_until(_EMAIL)
        kwargs = self.mock_client.get_item.call_args.kwargs
        self.assertIn("ProjectionExpression", kwargs)

    def test_uses_email_as_key(self) -> None:
        """Must pass email as the partition key in the get_item request."""
        self.mock_client.get_item.return_value = {}
        self.repo.get_lockout_until(_EMAIL)
        kwargs = self.mock_client.get_item.call_args.kwargs
        self.assertEqual(kwargs["Key"], {"email": {"S": _EMAIL}})


class TestIncrementFailedAttempts(_RepoTestCase):
    """Tests for LoginAttemptsRepository.increment_failed_attempts."""

    def test_returns_new_count_from_response(self) -> None:
        """Must return the updated failed_attempts count from the DynamoDB response."""
        self.mock_client.update_item.return_value = {
            "Attributes": {"failed_attempts": {"N": "3"}}
        }
        self.assertEqual(self.repo.increment_failed_attempts(_EMAIL), 3)

    def test_uses_add_expression(self) -> None:
        """Must use an ADD update expression for atomic increment."""
        self.mock_client.update_item.return_value = {
            "Attributes": {"failed_attempts": {"N": "1"}}
        }
        self.repo.increment_failed_attempts(_EMAIL)
        kwargs = self.mock_client.update_item.call_args.kwargs
        self.assertIn("ADD", kwargs["UpdateExpression"])

    def test_returns_zero_on_client_error(self) -> None:
        """Must return 0 without raising when a ClientError occurs."""
        self.mock_client.update_item.side_effect = _GENERIC_CLIENT_ERROR
        self.assertEqual(self.repo.increment_failed_attempts(_EMAIL), 0)


class TestSetLockout(_RepoTestCase):
    """Tests for LoginAttemptsRepository.set_lockout."""

    def test_calls_update_item_with_lockout_timestamp(self) -> None:
        """Must call update_item with the lockout_until timestamp as a Number."""
        self.repo.set_lockout(_EMAIL, _LOCKOUT_TS)
        self.mock_client.update_item.assert_called_once()
        kwargs = self.mock_client.update_item.call_args.kwargs
        self.assertIn(":lu", kwargs["ExpressionAttributeValues"])
        self.assertEqual(
            kwargs["ExpressionAttributeValues"][":lu"], {"N": str(_LOCKOUT_TS)}
        )

    def test_uses_set_expression(self) -> None:
        """Must use a SET update expression."""
        self.repo.set_lockout(_EMAIL, _LOCKOUT_TS)
        kwargs = self.mock_client.update_item.call_args.kwargs
        self.assertIn("SET", kwargs["UpdateExpression"])

    def test_swallows_client_error(self) -> None:
        """Must not raise when a ClientError occurs."""
        self.mock_client.update_item.side_effect = _GENERIC_CLIENT_ERROR
        self.repo.set_lockout(_EMAIL, _LOCKOUT_TS)  # must not raise


class TestResetAttempts(_RepoTestCase):
    """Tests for LoginAttemptsRepository.reset_attempts."""

    def test_calls_delete_item_with_email_key(self) -> None:
        """reset_attempts must delete the item keyed by email."""
        self.repo.reset_attempts(_EMAIL)
        self.mock_client.delete_item.assert_called_once()
        kwargs = self.mock_client.delete_item.call_args.kwargs
        self.assertEqual(kwargs["Key"], {"email": {"S": _EMAIL}})

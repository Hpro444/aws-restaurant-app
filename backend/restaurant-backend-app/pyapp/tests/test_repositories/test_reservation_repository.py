"""Tests for ReservationRepository slot-booked query helpers."""

import unittest
import uuid
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from repositories.reservation_repository import (
        ReservationRepository,  # type: ignore[import-untyped]
    )

_SLOT_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_SLOT_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_SLOT_3_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

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

        self.repo = ReservationRepository()
        self.repo._resolve_table_name = MagicMock(return_value="test-reservations")


class TestIsSlotBooked(_RepoTestCase):
    """Tests for ReservationRepository.is_slot_booked."""

    def test_returns_true_when_query_returns_active_item(self) -> None:
        """Query returns item with active status means slot is booked."""
        reservation_item = {
            "id": {"S": str(uuid.uuid4())},
            "slot": {"S": str(_SLOT_1_ID)},
            "customer_id": {"S": str(uuid.uuid4())},
            "waiter_id": {"S": str(uuid.uuid4())},
            "created_at": {"S": "2026-05-16T12:00:00+00:00"},
            "number_of_guests": {"N": "2"},
            "status": {"S": "RESERVED"},
        }
        self.mock_client.query.return_value = {"Items": [reservation_item]}

        self.assertTrue(self.repo.is_slot_booked(_SLOT_1_ID))

    def test_returns_false_when_query_returns_no_items(self) -> None:
        """No matching items means slot is not booked."""
        self.mock_client.query.return_value = {"Items": []}

        self.assertFalse(self.repo.is_slot_booked(_SLOT_1_ID))

    def test_returns_false_on_client_error(self) -> None:
        """A DynamoDB ClientError must return False without raising."""
        self.mock_client.query.side_effect = _GENERIC_CLIENT_ERROR

        self.assertFalse(self.repo.is_slot_booked(_SLOT_1_ID))

    def test_checks_status_in_python_not_server_filter(self) -> None:
        """Query must use Limit=1 without FilterExpression; status checked in Python."""
        self.mock_client.query.return_value = {"Items": []}

        self.repo.is_slot_booked(_SLOT_1_ID)

        kwargs = self.mock_client.query.call_args.kwargs
        self.assertEqual(kwargs["IndexName"], "slot-index")
        self.assertEqual(kwargs["KeyConditionExpression"], "slot = :sid")
        self.assertEqual(kwargs["Limit"], 1)
        # No FilterExpression: status is checked in Python after deserialization
        self.assertNotIn("FilterExpression", kwargs)


class TestFindBookedSlotIds(_RepoTestCase):
    """Tests for ReservationRepository.find_booked_slot_ids."""

    def test_returns_only_booked_slot_ids(self) -> None:
        """Must include IDs where is_slot_booked is True and exclude others."""
        self.repo.is_slot_booked = MagicMock(
            side_effect=lambda sid: sid in {_SLOT_1_ID, _SLOT_3_ID}
        )

        result = self.repo.find_booked_slot_ids({_SLOT_1_ID, _SLOT_2_ID, _SLOT_3_ID})

        self.assertEqual(result, {_SLOT_1_ID, _SLOT_3_ID})
        self.assertEqual(self.repo.is_slot_booked.call_count, 3)

    def test_returns_empty_set_when_input_empty(self) -> None:
        """Empty input must return empty result and not call is_slot_booked."""
        self.repo.is_slot_booked = MagicMock(return_value=False)

        result = self.repo.find_booked_slot_ids(set())

        self.assertEqual(result, set())
        self.repo.is_slot_booked.assert_not_called()

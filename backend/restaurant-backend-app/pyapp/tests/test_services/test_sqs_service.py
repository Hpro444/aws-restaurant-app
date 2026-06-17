"""Unit tests for SqsService generic SQS publisher."""

import json
import unittest
from unittest.mock import MagicMock

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from dto.reservation_event import ReservationEventMessage, ReservationEventType
    from dto.reservation_management import AllowedActions
    from enums import ReservationStatus
    from services.sqs_service import SqsService


QUEUE_URL = "https://sqs.eu-west-3.amazonaws.com/111111111111/test-queue"


def _make_settings(queue_url: str = QUEUE_URL) -> MagicMock:
    """Return a mock AppConfig with the given queue URL."""
    settings = MagicMock()
    settings.aws_region = "eu-west-3"
    settings.event_queue_url = queue_url
    return settings


def _make_message(event_type=ReservationEventType.CREATED) -> ReservationEventMessage:
    """Return a flat ReservationEventMessage with test data."""
    return ReservationEventMessage(
        event_type=event_type,
        timestamp="2026-06-01T12:00:00Z",
        reservation_id="res-123",
        status=ReservationStatus.RESERVED,
        customer_id="cust-456",
        waiter_id=None,
        location_id="loc-789",
        location_address="48 Rustaveli Avenue",
        table_number=3,
        date="2026-07-01",
        time_from="12:00",
        time_to="13:30",
        guests_number=2,
        allowed_actions=AllowedActions(can_edit=True, can_cancel=True),
        cutoff_reason=None,
    )


class TestSqsServicePublish(unittest.TestCase):
    """Tests for SqsService.publish generic behaviour."""

    def _make_service(self, queue_url: str = QUEUE_URL) -> tuple[SqsService, MagicMock]:
        """Return (service, mock_boto3_client) with the given queue URL."""
        mock_client = MagicMock()
        service = SqsService(settings=_make_settings(queue_url), client=mock_client)
        return service, mock_client

    def test_skips_when_queue_url_empty(self):
        """SqsService.publish does not call send_message when queue_url is empty."""
        service, mock_client = self._make_service(queue_url="")
        service.publish("", _make_message())
        mock_client.send_message.assert_not_called()

    def test_calls_send_message_with_correct_queue_url(self):
        """send_message receives the exact queue URL passed to publish."""
        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, _make_message())
        mock_client.send_message.assert_called_once()
        call_kwargs = mock_client.send_message.call_args.kwargs
        self.assertEqual(call_kwargs["QueueUrl"], QUEUE_URL)

    def test_message_body_is_valid_json(self):
        """MessageBody is a valid JSON string."""
        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, _make_message())
        body = mock_client.send_message.call_args.kwargs["MessageBody"]
        parsed = json.loads(body)
        self.assertIsInstance(parsed, dict)

    def test_message_body_uses_camel_case_event_type_alias(self):
        """MessageBody uses the camelCase alias 'eventType', not 'event_type'."""
        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, _make_message(ReservationEventType.FINISHED))
        body = json.loads(mock_client.send_message.call_args.kwargs["MessageBody"])
        self.assertIn("eventType", body)
        self.assertEqual(body["eventType"], "FINISHED")
        self.assertNotIn("event_type", body)

    def test_message_body_contains_reservation_id_flat(self):
        """ReservationId is a top-level key in the flat message (no nested sub-object)."""
        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, _make_message())
        body = json.loads(mock_client.send_message.call_args.kwargs["MessageBody"])
        self.assertIn("reservationId", body)
        self.assertEqual(body["reservationId"], "res-123")
        self.assertNotIn("reservation", body)

    def test_message_body_contains_timestamp(self):
        """MessageBody has a non-empty 'timestamp' field."""
        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, _make_message())
        body = json.loads(mock_client.send_message.call_args.kwargs["MessageBody"])
        self.assertIn("timestamp", body)
        self.assertTrue(body["timestamp"])

    def test_swallows_boto3_exception(self):
        """No exception propagates when send_message raises."""
        service, mock_client = self._make_service()
        mock_client.send_message.side_effect = RuntimeError("connection refused")
        try:
            service.publish(QUEUE_URL, _make_message())
        except Exception as exc:
            self.fail(f"publish raised unexpectedly: {exc}")

    def test_accepts_any_base_model(self):
        """Publish works with any Pydantic BaseModel, not just ReservationEventMessage."""
        from pydantic import BaseModel

        class ArbitraryPayload(BaseModel):
            """Arbitrary payload for testing generic publish."""

            value: int

        service, mock_client = self._make_service()
        service.publish(QUEUE_URL, ArbitraryPayload(value=42))
        mock_client.send_message.assert_called_once()
        body = json.loads(mock_client.send_message.call_args.kwargs["MessageBody"])
        self.assertEqual(body["value"], 42)

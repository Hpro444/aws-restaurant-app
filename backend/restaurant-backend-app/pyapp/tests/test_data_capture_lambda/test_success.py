"""Tests for the data capture lambda success path."""

import json

from pyapp.tests.test_data_capture_lambda import DataCaptureLambdaLambdaTestCase

_SQS_EVENT = {
    "Records": [
        {
            "messageId": "test-msg-id",
            "receiptHandle": "test-receipt",
            "body": json.dumps(
                {
                    "eventType": "CREATED",
                    "reservationId": "11111111-1111-1111-1111-111111111111",
                    "timestamp": "2026-06-04T10:00:00Z",
                    "status": "RESERVED",
                    "date": "2026-06-04",
                    "timeFrom": "10:00",
                    "timeTo": "11:30",
                    "guestsNumber": 2,
                    "allowedActions": {"canEdit": True, "canCancel": True},
                }
            ),
            "eventSource": "aws:sqs",
        }
    ]
}


class TestSuccess(DataCaptureLambdaLambdaTestCase):
    """Verifies that the lambda handles valid SQS events successfully."""

    def test_success(self):
        """Assert handle_request processes a single SQS record without error."""
        result = self.HANDLER.handle_request(_SQS_EVENT, {})
        self.assertEqual(json.loads(result.body)["processed"], 1)

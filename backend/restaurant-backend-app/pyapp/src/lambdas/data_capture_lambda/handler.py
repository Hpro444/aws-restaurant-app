"""Lambda handler that processes reservation and feedback events from SQS."""

import json

from commons import LambdaResponse, build_response
from commons.abstract_lambda import AbstractLambda
from commons.log_helper import get_logger
from dto.feedback_event import FeedbackEventMessage
from dto.reservation_event import ReservationEventMessage
from services.location_report_service import LocationReportService
from services.waiter_report_service import WaiterReportService

_LOG = get_logger(__name__)


class DataCaptureLambda(AbstractLambda):
    """Processes SQS events and maintains the WaiterReport and LocationReport tables."""

    def __init__(self) -> None:
        """Initialise the singleton report services on cold start."""
        super().__init__()
        self._waiter_report_service = WaiterReportService()
        self._location_report_service = LocationReportService()

    def validate_request(self, event) -> dict:
        """Return empty dict; SQS events require no additional validation."""
        return {}

    def handle_request(self, event, context) -> LambdaResponse:
        """Dispatch each SQS record to all report-service handlers.

        Reservation events are identified by the presence of a ``reservationId``
        key; feedback events by the presence of a ``feedbackId`` key. Each
        record is dispatched to both the waiter and location report services so
        one malformed message does not abort the rest of the batch.
        """
        records = event.get("Records", [])
        processed = 0
        for record in records:
            try:
                body = json.loads(record.get("body", "{}"))
                if "feedbackId" in body:
                    msg = FeedbackEventMessage.model_validate(body)
                    self._waiter_report_service.handle_feedback_event(msg)
                    self._location_report_service.handle_feedback_event(msg)
                else:
                    msg = ReservationEventMessage.model_validate(body)
                    self._waiter_report_service.handle_reservation_event(msg)
                    self._location_report_service.handle_reservation_event(msg)
                processed += 1
            except Exception:
                _LOG.error("Failed to process SQS record", exc_info=True, record=record)
        return build_response({"processed": processed})


HANDLER = DataCaptureLambda()


def lambda_handler(event, context):
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

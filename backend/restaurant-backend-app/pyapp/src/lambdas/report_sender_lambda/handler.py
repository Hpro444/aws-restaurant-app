"""Lambda handler for sending weekly reports via SES."""

from commons import LambdaResponse, build_response
from commons.abstract_lambda import AbstractLambda
from services.report_sender_service import ReportSenderService


class ReportSenderLambda(AbstractLambda):
    """Generates current-week report CSVs and sends them by email."""

    def __init__(self) -> None:
        """Initialise dependencies once per Lambda container."""
        super().__init__()
        self._report_sender_service = ReportSenderService()

    def validate_request(self, event) -> dict:
        """Return empty validation errors because no request schema is required."""
        return {}

    def handle_request(self, event, context) -> LambdaResponse:
        """Generate and email the report for the current ISO week."""
        summary = self._report_sender_service.send_weekly_report()
        return build_response(summary)


HANDLER = ReportSenderLambda()


def lambda_handler(event, context):
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

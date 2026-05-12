"""Abstract base class defining the Lambda handler contract."""

import json
from abc import abstractmethod
from typing import Any

from enums.http_status_code import HttpStatusCode

from commons import ApplicationException, build_response
from commons.log_helper import get_logger

_LOG = get_logger(__name__)


class AbstractLambda:
    """Base class for all Lambda handlers; provides routing and error-handling scaffolding."""

    @abstractmethod
    def validate_request(self, event: dict) -> dict:
        """Validate event attributes before the request is handled.

        Args:
            event: Lambda incoming event dict from API Gateway.

        Returns:
            A dict mapping field names to error messages; empty if valid.
        """
        pass

    @abstractmethod
    def handle_request(self, event: dict, context: Any) -> dict:
        """Execute the Lambda function logic for a validated request.

        Args:
            event: Lambda event dict from API Gateway.
            context: Lambda context object.

        Returns:
            A Lambda proxy response dict.
        """
        pass

    def lambda_handler(self, event: dict, context: Any) -> dict | None:
        """Entry point that validates, dispatches, and catches exceptions.

        Args:
            event: Lambda event dict from API Gateway.
            context: Lambda context object.

        Returns:
            A Lambda proxy response dict, or None for warm-up events.
        """
        try:
            _LOG.debug(f'Request: {event}')
            if event.get('warm_up'):
                return None
            errors = self.validate_request(event=event)
            if errors:
                return build_response(code=HttpStatusCode.RESPONSE_BAD_REQUEST_CODE,
                                      content=errors)
            execution_result = self.handle_request(event=event,
                                                   context=context)
            _LOG.debug(f'Response: {execution_result}')
            return execution_result
        except ApplicationException as e:
            _LOG.error(f'Error occurred; Event: {event}; Error: {e}')
            return {
                'statusCode': e.code,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(e.content),
            }
        except Exception as e:
            _LOG.error(
                f'Unexpected error occurred; Event: {event}; Error: {e}')
            return {
                'statusCode': HttpStatusCode.RESPONSE_INTERNAL_SERVER_ERROR,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps('Internal server error'),
            }

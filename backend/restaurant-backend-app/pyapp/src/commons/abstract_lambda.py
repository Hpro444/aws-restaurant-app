"""Abstract base class defining the Lambda handler contract."""

import json
from abc import ABC, abstractmethod
from typing import Any

from enums import HttpStatusCode

from commons import ApplicationException, build_response
from commons.app_config import AppConfig
from commons.log_helper import logger
from commons.response import LambdaResponse

_config = AppConfig()


class AbstractLambda(ABC):
    """Base class for all Lambda handlers; provides routing and error-handling scaffolding."""

    @abstractmethod
    def validate_request(self, event: dict) -> dict:
        """Validate event attributes before the request is handled.

        Args:
            event: Lambda incoming event dict from API Gateway.

        Returns:
            A dict mapping field names to error messages; empty if valid.

        """

    @abstractmethod
    def handle_request(self, event: dict, context: Any) -> LambdaResponse:
        """Execute the Lambda function logic for a validated request.

        Args:
            event: Lambda event dict from API Gateway.
            context: Lambda context object.

        Returns:
            A :class:`LambdaResponse` instance.

        """

    def lambda_handler(self, event: dict, context: Any) -> dict | None:
        """Entry point that validates, dispatches, and catches exceptions.

        Args:
            event: Lambda event dict from API Gateway.
            context: Lambda context object.

        Returns:
            A Lambda proxy response dict, or None for warm-up events.

        """
        try:
            logger.debug("Request", request=event)
            if event.get("warm_up"):
                return None
            errors = self.validate_request(event=event)
            if errors:
                response = build_response(
                    code=HttpStatusCode.RESPONSE_BAD_REQUEST_CODE, content=errors
                ).model_dump()
            else:
                execution_result = self.handle_request(event=event, context=context)
                logger.debug("Response", response=execution_result.model_dump())
                response = execution_result.model_dump()
        except ApplicationException as e:
            if e.code >= 500:
                logger.error(
                    "Application error", request=event, status_code=e.code, error=str(e)
                )
            else:
                logger.info(
                    "Client error", request=event, status_code=e.code, error=str(e)
                )
            response = LambdaResponse(
                statusCode=e.code, body=json.dumps(e.content)
            ).model_dump()
        except Exception as e:
            logger.error("Unexpected error", request=event, error=str(e))
            response = LambdaResponse(
                statusCode=HttpStatusCode.RESPONSE_INTERNAL_SERVER_ERROR,
                body=json.dumps({"message": "Internal server error"}),
            ).model_dump()
        request_origin = (event.get("headers") or {}).get(
            "origin", (event.get("headers") or {}).get("Origin", "")
        )
        allowed_origin = (
            request_origin
            if request_origin in _config.cors_origins
            else _config.cors_origins[0]
        )
        if "headers" not in response:
            response["headers"] = {}
        response["headers"]["Access-Control-Allow-Origin"] = allowed_origin
        response["headers"]["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type"
        )
        response["headers"]["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        return response

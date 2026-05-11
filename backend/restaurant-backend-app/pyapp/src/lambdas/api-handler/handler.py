"""Lambda handler for the restaurant API."""

import json

from pydantic import ValidationError

from commons import build_response
from commons.abstract_lambda import AbstractLambda
from commons.log_helper import get_logger
from dto.sign_up_request import SignUpRequest
from dto.sign_up_response import SignUpResponse
from services.cognito_service import CognitoService

_LOG = get_logger(__name__)


class ApiHandler(AbstractLambda):
    """Handles all routed requests from API Gateway for the restaurant backend."""

    def __init__(self):
        """Initialise service dependencies."""
        self._cognito_service = CognitoService()

    def validate_request(self, event) -> dict:
        """Check that a request body is present before processing.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A dict with an error message if the body is absent, otherwise empty.
        """
        if event.get("body") is None:
            return {"body": "Request body is required"}
        return {}

    def handle_request(self, event, context):
        """Route the event by path and method, then dispatch to the correct handler.

        Args:
            event: The Lambda event dict from API Gateway.
            context: The Lambda context object.

        Returns:
            A dict with 'code' and 'body' keys representing the HTTP response.
        """
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if path == "/auth/sign-up" and method == "POST":
            return self._sign_up(event)

        return build_response("Route not found", code=404)

    def _sign_up(self, event):
        """Process a user registration request and return a 201 response.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A dict with 'code' 201 and 'body' containing userId and message.
        """
        raw_body = event.get("body", "{}")
        try:
            payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            request = SignUpRequest(**payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            return build_response(str(exc), code=400)

        user_id = self._cognito_service.register_user(
            first_name=request.firstName,
            last_name=request.lastName,
            email=request.email,
            password=request.password,
        )

        response = SignUpResponse(
            userId=user_id,
            message="User registered successfully",
        )
        return build_response(response.model_dump(), code=201)


HANDLER = ApiHandler()


def lambda_handler(event, context):
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

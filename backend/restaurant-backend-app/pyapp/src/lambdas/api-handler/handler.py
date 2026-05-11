"""Lambda handler for the restaurant API."""

import json

from pydantic import ValidationError

from commons import build_response, raise_error_response
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
        """Return empty dict; all validation is handled in route methods via Pydantic.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            An empty dict — validation errors surface as 422 responses instead.
        """
        return {}

    def handle_request(self, event, context):
        """Route the event by path and method, then dispatch to the correct handler.

        Args:
            event: The Lambda event dict from API Gateway.
            context: The Lambda context object.

        Returns:
            A Lambda proxy response dict.
        """
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if path == "/auth/sign-up" and method == "POST":
            return self._sign_up(event)

        return build_response("Route not found", code=404)

    def _sign_up(self, event):
        """Process a user registration request and return a 201 response.

        Validates input via Pydantic (422 on failure), creates the user in
        Cognito, and returns the new userId on success.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A Lambda proxy response dict with statusCode 201 on success.
        """
        raw_body = event.get("body") or "{}"

        try:
            payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except json.JSONDecodeError:
            raise_error_response(422, [{"field": "body", "message": "Invalid JSON"}])

        try:
            request = SignUpRequest(**payload)
        except ValidationError as exc:
            errors = [
                {
                    "field": str(err["loc"][0]) if err["loc"] else "unknown",
                    "message": err["msg"],
                }
                for err in exc.errors()
            ]
            raise_error_response(422, errors)

        user_id = self._cognito_service.register_user(
            first_name=request.firstName,
            last_name=request.lastName,
            email=request.email,
            password=request.password,
        )

        return build_response(
            SignUpResponse(userId=user_id, message="User registered successfully").model_dump(),
            code=201,
        )


HANDLER = ApiHandler()


def lambda_handler(event, context):
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

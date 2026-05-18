"""Lambda handler for the restaurant API."""

import json
from typing import Any

from commons import LambdaResponse, build_response, raise_error_response
from commons.abstract_lambda import AbstractLambda
from dto.available_tables import AvailableTablesRequest
from dto.logout import LogoutRequest, LogoutResponse
from dto.refresh import RefreshRequest, RefreshResponse
from dto.sign_in import SignInRequest, SignInResponse
from dto.sign_up import SignUpRequest, SignUpResponse
from enums.http_status_code import HttpStatusCode
from pydantic import ValidationError
from services.cognito_service import CognitoService
from services.registration_service import RegistrationService
from services.table_availability_service import TableAvailabilityService


class ApiHandler(AbstractLambda):
    """Handles all routed requests from API Gateway for the restaurant backend."""

    def __init__(self) -> None:
        """Initialize service dependencies."""
        self._cognito_service = CognitoService()
        self._registration_service = RegistrationService(
            cognito_service=self._cognito_service
        )
        self._table_availability_service = TableAvailabilityService()

    def validate_request(self, event: dict) -> dict:
        """Return empty dict; all validation is handled in route methods via Pydantic.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            An empty dict — validation errors surface as 422 responses instead.

        """
        return {}

    def handle_request(self, event: dict, context: Any) -> LambdaResponse:
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

        if path == "/auth/sign-in" and method == "POST":
            return self._sign_in(event)

        if path == "/auth/refresh" and method == "POST":
            return self._refresh(event)

        if path == "/auth/logout" and method == "POST":
            return self._logout(event)

        if path == "/bookings/tables" and method == "GET":
            return self._get_available_tables(event)

        return build_response(
            "Route not found", code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE
        )

    def _parse_body(self, event: dict) -> dict:
        """Parse and return the JSON request body.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            Parsed body as a dict.

        """
        raw_body = event.get("body") or "{}"
        try:
            return json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except json.JSONDecodeError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [{"field": "body", "message": "Invalid JSON"}],
            )

    def _validate(self, model_cls, payload: dict):
        """Validate a payload dict against a Pydantic model, raising 422 on failure.

        Args:
            model_cls: The Pydantic model class to validate against.
            payload: Raw dict from the request body.

        Returns:
            A validated model instance.

        """
        try:
            return model_cls(**payload)
        except ValidationError as exc:
            errors = [
                {
                    "field": str(err["loc"][0]) if err["loc"] else "unknown",
                    "message": err["msg"],
                }
                for err in exc.errors()
            ]
            raise_error_response(HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY, errors)

    def _sign_up(self, event: dict) -> LambdaResponse:
        """Process a user registration request and return a 201 response.

        Automatically determines the user's role (Waiter or Customer) by checking
        the waiter-emails list (role-assignment table). Persists the user profile to the appropriate
        DynamoDB table after Cognito registration.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A Lambda proxy response dict with statusCode 201 on success.

        """
        request: SignUpRequest = self._validate(SignUpRequest, self._parse_body(event))

        user_id = self._registration_service.register_user(request)

        return build_response(
            SignUpResponse(
                user_id=user_id, message="User registered successfully"
            ).model_dump(),
            code=HttpStatusCode.RESPONSE_CREATED_CODE,
        )

    def _sign_in(self, event: dict) -> LambdaResponse:
        """Process a login request and return tokens on success.

        Both bad email and bad password return 401 with the same generic message
        to prevent user enumeration. Lockout enforcement (attempt tracking, 423
        responses) is handled inside CognitoService.authenticate_user.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A Lambda proxy response dict with statusCode 200 on success.

        """
        request: SignInRequest = self._validate(SignInRequest, self._parse_body(event))

        auth = self._cognito_service.authenticate_user(
            email=request.email,
            password=request.password,
        )

        return build_response(
            SignInResponse(
                access_token=auth.access_token,
                refresh_token=auth.refresh_token,
                username=auth.username,
                role=auth.role,
            ).model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _refresh(self, event: dict) -> LambdaResponse:
        """Exchange a refresh token for a new access token.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A Lambda proxy response dict with statusCode 200 and a new access token.

        """
        request: RefreshRequest = self._validate(
            RefreshRequest, self._parse_body(event)
        )

        access_token = self._cognito_service.refresh_tokens(
            refresh_token=request.refresh_token,
        )

        return build_response(
            RefreshResponse(access_token=access_token).model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _logout(self, event: dict) -> LambdaResponse:
        """Revoke the user's refresh token, invalidating their session.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A Lambda proxy response dict with statusCode 200 on success.

        """
        request: LogoutRequest = self._validate(LogoutRequest, self._parse_body(event))
        self._cognito_service.logout_user(refresh_token=request.refresh_token)
        return build_response(
            LogoutResponse(message="Logged out successfully").model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    @staticmethod
    def _parse_query_params(event: dict) -> dict:
        """Extract query string parameters from API Gateway event."""
        return event.get("queryStringParameters") or {}

    def _get_available_tables(self, event: dict):
        """Handle GET /bookings/tables.

        Query params:
            - location_id (required): UUID of the restaurant location.
            - date (required): Booking date in YYYY-MM-DD format.
            - guests_number (required): Minimum number of guests (1-10).
            - from_time (optional): Start time filter in HH:MM format.
            - to_time (optional): End time filter in HH:MM format.

        Filtering logic (AND):
            1. Location — only tables at the specified location.
            2. Guest count — only tables with capacity >= guests_number.
            3. Timeslot — only slots on the given date that are not reserved;
               optionally narrowed to a from_time/to_time window.

        Returns available tables with their free time slots,
        or an empty list when no tables match.

        """
        params = self._parse_query_params(event)

        # Safe conversion of guests_number from string to int
        raw_guests = params.get("guests_number", "")
        try:
            guests_number = int(raw_guests) if raw_guests else None
        except ValueError:
            return raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [{"field": "guests_number", "message": "Must be a valid integer"}],
            )
        except TypeError:
            return raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [{"field": "guests_number", "message": "Must be a valid integer"}],
            )

        # Check for missing required parameters before Pydantic validation
        missing_fields = []
        if not params.get("location_id"):
            missing_fields.append(
                {"field": "location_id", "message": "This field is required"}
            )
        if not params.get("date"):
            missing_fields.append(
                {"field": "date", "message": "This field is required"}
            )
        if guests_number is None:
            missing_fields.append(
                {"field": "guests_number", "message": "This field is required"}
            )

        if missing_fields:
            return raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY, missing_fields
            )

        # Validate all params through Pydantic (date format, UUID, range, time)
        request = self._validate(
            AvailableTablesRequest,
            {
                "location_id": params.get("location_id", ""),
                "date": params.get("date", ""),
                "guests_number": guests_number,
                "from_time": params.get("from_time") or params.get("from"),
                "to_time": params.get("to_time") or params.get("to"),
            },
        )

        # Compute availability with all filters applied
        response = self._table_availability_service.get_available_tables(
            location_id=request.location_id,
            booking_date=request.date,
            guests_number=request.guests_number,
            from_time=request.from_time,
            to_time=request.to_time,
        )

        return build_response(
            response.model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )


HANDLER = ApiHandler()


def lambda_handler(event: dict, context: Any) -> dict | None:
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

"""Lambda handler for the restaurant API."""

import json
from typing import Any
from uuid import UUID

from commons import LambdaResponse, build_response, raise_error_response
from commons.abstract_lambda import AbstractLambda
from dto.available_tables import AvailableTablesRequest
from dto.create_booking import CreateBookingRequest
from dto.error_response import FieldError, ValidationErrorResponse
from dto.locations import LocationAddressResponse, LocationResponse
from dto.logout import LogoutRequest, LogoutResponse
from dto.refresh import RefreshRequest, RefreshResponse
from dto.reservation_management import UpdateReservationRequest
from dto.sign_in import SignInRequest, SignInResponse
from dto.sign_up import SignUpRequest, SignUpResponse
from dto.user_profile import ProfileResponse, UpdateProfileRequest
from enums.http_status_code import HttpStatusCode
from enums.user_role import UserRole
from pydantic import ValidationError
from repositories.admin_emails_repository import AdminEmailsRepository
from repositories.admin_repository import AdminRepository
from repositories.customer_repository import CustomerRepository
from repositories.waiter_repository import WaiterRepository
from services.booking_service import BookingService
from services.cognito_service import CognitoService
from services.dishes_service import DishesService
from services.feedback_service import FeedbackService
from services.locations_service import LocationsService
from services.registration_service import RegistrationService
from services.reservation_management_service import ReservationManagementService
from services.table_availability_service import TableAvailabilityService
from services.user_profile_service import UserProfileService


class ApiHandler(AbstractLambda):
    """Handles all routed requests from API Gateway for the restaurant backend."""

    def __init__(self) -> None:
        """Initialize shared dependencies and services."""
        # Shared dependencies
        self._cognito_service = CognitoService()
        self._customer_repository = CustomerRepository()
        self._waiter_repository = WaiterRepository()
        self._admin_repository = AdminRepository()
        self._admin_emails_repository = AdminEmailsRepository()

        # Services (reuse shared dependencies)
        self._registration_service = RegistrationService(
            cognito_service=self._cognito_service,
            waiter_repository=self._waiter_repository,
            customer_repository=self._customer_repository,
            admin_repository=self._admin_repository,
            admin_emails_repository=self._admin_emails_repository,
        )
        self._user_profile_service = UserProfileService(
            cognito_service=self._cognito_service,
            customer_repository=self._customer_repository,
            waiter_repository=self._waiter_repository,
            admin_repository=self._admin_repository,
        )
        self._locations_service = LocationsService()
        self._table_availability_service = TableAvailabilityService()
        self._booking_service = BookingService()
        self._reservation_management_service = ReservationManagementService()
        self._dishes_service = DishesService()
        self._feedback_service = FeedbackService()

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
        resource = event.get("resource", "")

        if method == "OPTIONS":
            return build_response("", code=HttpStatusCode.RESPONSE_OK_CODE)

        if path == "/auth/sign-up" and method == "POST":
            return self._sign_up(event)

        if path == "/auth/sign-in" and method == "POST":
            return self._sign_in(event)

        if path == "/auth/refresh" and method == "POST":
            return self._refresh(event)

        if path == "/auth/logout" and method == "POST":
            return self._logout(event)

        if path == "/users/profile" and method == "GET":
            return self._get_user_profile(event)

        if path == "/users/profile" and method == "PUT":
            return self._update_user_profile(event)

        if path == "/locations/select-options" and method == "GET":
            return self._get_location_addresses()

        # TODO: there should be an universal helper function to handle paths like that end with "/{id}", like here "/locations/{id}"
        if method == "GET" and (
            resource == "/locations/{id}" or self._is_single_location_path(path)
        ):
            return self._get_location_by_id(event)

        if path == "/locations" and method == "GET":
            return self._get_locations()

        if path == "/bookings/tables" and method == "GET":
            return self._get_available_tables(event)

        if path == "/bookings/client" and method == "POST":
            return self._create_booking(event)

        if path == "/bookings/client" and method == "GET":
            return self._list_dashboard_bookings(event)

        if (
            path.startswith("/bookings/client/")
            and not path.endswith("/cancel")
            and method == "GET"
        ):
            return self._get_booking(event)

        if (
            path.endswith("/cancel")
            and path.startswith("/bookings/client/")
            and method == "DELETE"
        ):
            return self._cancel_booking(event)

        if path.startswith("/bookings/client/") and method == "PUT":
            return self._update_booking(event)

        if path == "/dishes/popular" and method == "GET":
            return self._get_popular_dishes(event)

        if (
            path.startswith("/locations/")
            and path.endswith("/speciality-dishes")
            and method == "GET"
        ):
            return self._get_speciality_dishes_by_location(event)

        if (
            path.startswith("/locations/")
            and path.endswith("/feedbacks")
            and method == "GET"
        ):
            return self._get_feedbacks_by_location(event)

        return build_response(
            "Route not found", code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE
        )

    def _extract_access_token(self, event: dict) -> str:
        """Extract and return the access token from the Authorization header."""
        headers = event.get("headers") or {}
        authorization = headers.get("Authorization") or headers.get("authorization")
        if not isinstance(authorization, str):
            raise_error_response(
                HttpStatusCode.RESPONSE_UNAUTHORIZED,
                "Missing or invalid Authorization header",
            )

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNAUTHORIZED,
                "Missing or invalid Authorization header",
            )
        return token

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
                ValidationErrorResponse(
                    errors=[FieldError(field="body", message="Invalid JSON")]
                ).model_dump(),
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
                FieldError(
                    field=str(err["loc"][0]) if err["loc"] else "unknown",
                    message=err["msg"],
                )
                for err in exc.errors()
            ]
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(errors=errors).model_dump(),
            )

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

        self._registration_service.register_user(request)

        return build_response(
            SignUpResponse(message="User registered successfully").model_dump(),
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

    def _get_user_profile(self, event: dict) -> LambdaResponse:
        """Return the authenticated user's profile from the role-specific table."""
        access_token = self._extract_access_token(event)
        _, role = self._cognito_service.get_identity_from_access_token(access_token)
        user = self._user_profile_service.get_user_profile(access_token)

        return build_response(
            ProfileResponse(
                first_name=user.fname,
                last_name=user.lname,
                image_url=user.image_url,
                email=user.email,
                role=role,
            ).model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _update_user_profile(self, event: dict) -> LambdaResponse:
        """Update and return the authenticated user's profile."""
        access_token = self._extract_access_token(event)
        _, role = self._cognito_service.get_identity_from_access_token(access_token)
        request: UpdateProfileRequest = self._validate(
            UpdateProfileRequest, self._parse_body(event)
        )
        user = self._user_profile_service.update_user_profile(access_token, request)

        return build_response(
            ProfileResponse(
                first_name=user.fname,
                last_name=user.lname,
                image_url=user.image_url,
                email=user.email,
                role=role,
            ).model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_locations(self) -> LambdaResponse:
        """Return all restaurant locations for the public locations page."""
        locations: list[LocationResponse] = self._locations_service.get_locations()
        return build_response(
            [location.model_dump() for location in locations],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_location_addresses(self) -> LambdaResponse:
        """Return all location addresses for location pickers and filters."""
        location_options: list[LocationAddressResponse] = (
            self._locations_service.get_location_addresses()
        )
        return build_response(
            [location_option.model_dump() for location_option in location_options],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_location_by_id(self, event: dict) -> LambdaResponse:
        """Return a single location for GET /locations/{id}."""
        raw_id = self._extract_path_segment(event, 1)
        if raw_id is None:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field="id", message="Missing location id")]
                ).model_dump(),
            )

        try:
            location_id = UUID(raw_id)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field="id", message="Must be a valid UUID")]
                ).model_dump(),
            )

        location = self._locations_service.get_location_by_id(location_id)
        if location is None:
            raise_error_response(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                ValidationErrorResponse(
                    errors=[FieldError(field="id", message="Location not found")]
                ).model_dump(),
            )

        return build_response(
            location.model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    @staticmethod
    def _is_single_location_path(path: str) -> bool:
        """Return True only for concrete paths shaped as /locations/{id}."""
        parts = [part for part in path.split("/") if part]
        return len(parts) == 2 and parts[0] == "locations"

    @staticmethod
    def _parse_query_params(event: dict) -> dict:
        """Extract query string parameters from API Gateway event."""
        return event.get("queryStringParameters") or {}

    # TODO: ovo treba da zameni sa _extract_path_segment da se koristi univerzalna funkcija
    @staticmethod
    def _extract_booking_id(path: str, suffix: str | None = None) -> str:
        """Extract booking UUID from path and validate format.

        Expected forms:
            - /bookings/client/{reservationId}
            - /bookings/client/{reservationId}/cancel
        """
        base = "/bookings/client/"
        if not path.startswith(base):
            raise_error_response(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Route not found",
            )

        tail = path[len(base) :]
        if suffix:
            expected_suffix = f"/{suffix}"
            if not tail.endswith(expected_suffix):
                raise_error_response(
                    HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                    "Route not found",
                )
            tail = tail[: -len(expected_suffix)]

        reservation_id = tail.strip("/")
        try:
            UUID(reservation_id)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="reservationId", message="Must be a valid UUID"
                        )
                    ]
                ).model_dump(),
            )
        except TypeError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="reservationId", message="Must be a valid UUID"
                        )
                    ]
                ).model_dump(),
            )

        return reservation_id

    @staticmethod
    def _extract_path_segment(event: dict, position: int) -> str | None:
        """Extract a path segment by position for parametrized routes.

        For /locations/{id}/speciality-dishes, position=1 returns the id value.
        Tries pathParameters first (API Gateway), then falls back to parsing the path string.

        Args:
            event: Lambda event from API Gateway.
            position: 0-based position of the segment to extract (1 for id in /locations/{id}/...).

        Returns:
            The path segment value, or None if not found.

        """
        path_params = event.get("pathParameters") or {}
        if "id" in path_params:
            return path_params.get("id")

        path = event.get("path", "")
        parts = [part for part in path.split("/") if part]
        if position < len(parts):
            return parts[position]

        return None

    def _get_available_tables(self, event: dict):
        """Handle GET /bookings/tables.

        Query params:
            - location_id (required): UUID of the restaurant location.
            - date (required): Booking date in YYYY-MM-DD format.
            - guests_number (required): Minimum number of guests (1-10).
            - from_time (optional): Start time filter in HH:MM format.
                Snapped to the nearest valid slot start; only tables with
                that slot free are returned, along with all subsequent
                free slots for the day.

        Filtering logic (AND):
            1. Location — only tables at the specified location.
            2. Guest count — only tables with capacity >= guests_number.
            3. Timeslot — only slots on the given date that are not reserved;
               optionally snapped to from_time and onwards.

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
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="guests_number", message="Must be a valid integer"
                        )
                    ]
                ).model_dump(),
            )
        except TypeError:
            return raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="guests_number", message="Must be a valid integer"
                        )
                    ]
                ).model_dump(),
            )

        # Check for missing required parameters before Pydantic validation
        missing_fields = []
        if not params.get("location_id"):
            missing_fields.append(
                FieldError(field="location_id", message="This field is required")
            )
        if not params.get("date"):
            missing_fields.append(
                FieldError(field="date", message="This field is required")
            )
        if guests_number is None:
            missing_fields.append(
                FieldError(field="guests_number", message="This field is required")
            )

        if missing_fields:
            return raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(errors=missing_fields).model_dump(),
            )

        # Validate all params through Pydantic (date format, UUID, range, time)
        request = self._validate(
            AvailableTablesRequest,
            {
                "location_id": params.get("location_id", ""),
                "date": params.get("date", ""),
                "guests_number": guests_number,
                "from_time": params.get("from_time") or params.get("from"),
            },
        )

        # Compute availability with all filters applied
        response = self._table_availability_service.get_available_tables(
            location_id=request.location_id,
            booking_date=request.date,
            guests_number=request.guests_number,
            from_time=request.from_time,
        )

        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _create_booking(self, event: dict) -> LambdaResponse:
        """Handle POST /bookings/client — create a reservation for a customer.

        Flow:
            1. Extract the access token and resolve the caller's identity.
            2. Only callers with ``UserRole.CUSTOMER`` may create a
               client-side reservation; anything else returns 403.
            3. Validate the JSON body against :class:`CreateBookingRequest`.
            4. Delegate persistence to :class:`BookingService.create_booking`.
            5. Return the saved reservation details for the UI success
               confirmation.

        """
        access_token = self._extract_access_token(event)
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        if role != UserRole.CUSTOMER.value:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only customers can create a client reservation",
            )

        request: CreateBookingRequest = self._validate(
            CreateBookingRequest, self._parse_body(event)
        )

        response = self._booking_service.create_booking(
            request=request,
            customer_id=user_id,
        )

        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _list_dashboard_bookings(self, event: dict) -> LambdaResponse:
        """Handle GET /bookings/client for customer/waiter dashboard reservations."""
        access_token = self._extract_access_token(event)
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )

        response = self._reservation_management_service.list_for_dashboard(
            actor_id=user_id,
            role=role,
        )
        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_booking(self, event: dict) -> LambdaResponse:
        """Handle GET /bookings/client/{reservationId}."""
        access_token = self._extract_access_token(event)
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        reservation_id = self._extract_booking_id(event.get("path", ""))

        response = self._reservation_management_service.get_reservation(
            reservation_id=reservation_id,
            actor_id=user_id,
            role=role,
        )

        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _update_booking(self, event: dict) -> LambdaResponse:
        """Handle PUT /bookings/client/{reservationId}."""
        access_token = self._extract_access_token(event)
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        reservation_id = self._extract_booking_id(event.get("path", ""))
        request: UpdateReservationRequest = self._validate(
            UpdateReservationRequest, self._parse_body(event)
        )

        response = self._reservation_management_service.update_reservation(
            reservation_id=reservation_id,
            request=request,
            actor_id=user_id,
            role=role,
        )

        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _cancel_booking(self, event: dict) -> LambdaResponse:
        """Handle PUT /bookings/client/{reservationId}/cancel."""
        access_token = self._extract_access_token(event)
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        reservation_id = self._extract_booking_id(
            event.get("path", ""), suffix="cancel"
        )

        response = self._reservation_management_service.cancel_reservation(
            reservation_id=reservation_id,
            actor_id=user_id,
            role=role,
        )

        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_popular_dishes(self, event: dict) -> LambdaResponse:
        """Handle GET /dishes/popular — retrieve all popular dishes across locations.

        Returns a list of all dishes marked as popular, across all restaurant
        locations. No authentication required (public endpoint).

        Uses a DynamoDB GSI on the ``popular`` flag for O(1) lookup efficiency.

        Returns:
            A Lambda proxy response dict with statusCode 200 and a JSON array
            of DishResponse objects, or an empty array if no popular dishes exist.

        """
        dishes = self._dishes_service.get_popular_dishes()
        return build_response(
            [dish.model_dump() for dish in dishes],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_speciality_dishes_by_location(self, event: dict) -> LambdaResponse:
        """Handle GET /locations/{id}/speciality-dishes.

        Returns speciality dishes for the requested location only.

        """
        location_id_str = self._extract_path_segment(event, 1)

        if location_id_str is None:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="id", message="Path parameter 'id' is required"
                        )
                    ]
                ).model_dump(),
            )

        try:
            location_id = UUID(location_id_str)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="id",
                            message="Path parameter 'id' must be a valid UUID",
                        )
                    ]
                ).model_dump(),
            )

        dishes = self._dishes_service.get_speciality_dishes_by_location(location_id)
        return build_response(
            [dish.model_dump() for dish in dishes],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_feedbacks_by_location(self, event: dict) -> LambdaResponse:
        """Handle GET /locations/{id}/feedbacks.

        Returns feedbacks for the requested location only.

        """
        location_id_str = self._extract_path_segment(event, 1)

        if location_id_str is None:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="id", message="Path parameter 'id' is required"
                        )
                    ]
                ).model_dump(),
            )

        try:
            location_id = UUID(location_id_str)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="id",
                            message="Path parameter 'id' must be a valid UUID",
                        )
                    ]
                ).model_dump(),
            )

        params = self._parse_query_params(event)

        type = params.get("type")
        if type is None:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field="type", message="This field is required")]
                ).model_dump(),
            )

        if type not in {"cuisine", "service"}:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="type", message="Must be one of: cuisine, service"
                        )
                    ]
                ).model_dump(),
            )

        sort_value = params.get("sort", "date,desc")
        sort_key, _, sort_direction = sort_value.partition(",")

        if sort_key not in {"date", "rate"}:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="sort",
                            message="Sort field must be one of: date, rate",
                        )
                    ]
                ).model_dump(),
            )

        if sort_direction and sort_direction not in {"asc", "desc"}:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="sort",
                            message="Sort direction must be one of: asc, desc",
                        )
                    ]
                ).model_dump(),
            )

        sort = [sort_value]

        raw_page = params.get("page", "0")
        raw_size = params.get("size", "20")
        try:
            page = int(raw_page)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [{"field": "page", "message": "Must be a valid integer"}],
            )
        except TypeError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field="page", message="Must be a valid integer")]
                ).model_dump(),
            )
        try:
            size = int(raw_size)
        except ValueError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                [{"field": "size", "message": "Must be a valid integer"}],
            )
        except TypeError:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field="size", message="Must be a valid integer")]
                ).model_dump(),
            )

        if page < 0:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="page", message="Must be greater than or equal to 0"
                        )
                    ]
                ).model_dump(),
            )

        if size < 1 or size > 100:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(field="size", message="Must be between 1 and 100")
                    ]
                ).model_dump(),
            )

        feedback_page = self._feedback_service.get_feedbacks(
            location_id=location_id,
            type=type,
            sort=sort,
            page=page,
            size=size,
        )

        content = feedback_page.get("content", [])
        feedback_page["content"] = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in content
        ]

        return build_response(
            feedback_page,
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )


HANDLER = ApiHandler()


def lambda_handler(event: dict, context: Any) -> dict | None:
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

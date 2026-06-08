"""Lambda handler for the restaurant API."""

import json
from typing import Any
from uuid import UUID

from commons import LambdaResponse, build_response, raise_error_response
from commons.abstract_lambda import AbstractLambda
from commons.router import Router
from dto.available_tables import AvailableTablesRequest, WaiterAvailableTablesRequest
from dto.create_booking import CreateBookingRequest
from dto.customers import CustomerResponse
from dto.dishes import GetDishesRequest
from dto.error_response import FieldError, ValidationErrorResponse
from dto.feedbacks import (
    LeaveFeedbackRequest,
    LeaveFeedbackResponse,
    PageFeedbackResponse,
)
from dto.locations import LocationAddressResponse, LocationResponse
from dto.logout import LogoutRequest, LogoutResponse
from dto.orders import CreateOrderRequest
from dto.refresh import RefreshRequest, RefreshResponse
from dto.reservation_management import UpdateReservationRequest
from dto.sign_in import SignInRequest, SignInResponse
from dto.sign_up import SignUpRequest, SignUpResponse
from dto.tables import TableDTO
from dto.user_profile import ProfileResponse, UpdateProfileRequest
from dto.waiter_reservations import GetWaiterReservationsRequest
from enums import HttpStatusCode, UserRole
from pydantic import ValidationError
from repositories.admin_emails_repository import AdminEmailsRepository
from repositories.admin_repository import AdminRepository
from repositories.customer_repository import CustomerRepository
from repositories.waiter_repository import WaiterRepository
from services.booking_service import BookingService
from services.cognito_service import CognitoService
from services.customers_service import CustomersService
from services.dishes_service import DishesService
from services.feedback_service import FeedbackService
from services.locations_service import LocationsService
from services.order_service import OrderService
from services.registration_service import RegistrationService
from services.reservation_management_service import ReservationManagementService
from services.sqs_service import SqsService
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
        self._sqs_service = SqsService()
        self._booking_service = BookingService(sqs_service=self._sqs_service)
        self._reservation_management_service = ReservationManagementService(
            sqs_service=self._sqs_service,
        )
        self._dishes_service = DishesService()
        self._feedback_service = FeedbackService(sqs_service=self._sqs_service)
        self._customers_service = CustomersService(
            customer_repository=self._customer_repository,
        )
        self._order_service = OrderService()

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
        method = event.get("httpMethod", "")

        if method == "OPTIONS":
            return build_response("", code=HttpStatusCode.RESPONSE_OK_CODE)
        return self._get_router().dispatch(event, context)

    def _build_router(self) -> Router:
        """Register all API routes once and return router instance."""
        router = Router()

        router.add("POST", "/auth/sign-up", self._sign_up)
        router.add("POST", "/auth/sign-in", self._sign_in)
        router.add("POST", "/auth/refresh", self._refresh)
        router.add("POST", "/auth/logout", self._logout)

        router.add("GET", "/users/profile", self._get_user_profile)
        router.add("PUT", "/users/profile", self._update_user_profile)
        router.add("GET", "/users/waiter/location", self._get_waiter_location)

        router.add("GET", "/locations/select-options", self._get_location_addresses)
        router.add(
            "GET", "/locations/{id}/valid-slot-times", self._get_valid_slot_times
        )

        router.add("GET", "/locations", self._get_locations)
        router.add("GET", "/locations/{id}", self._get_location_by_id)
        router.add(
            "GET",
            "/locations/{id}/speciality-dishes",
            self._get_speciality_dishes_by_location,
        )
        router.add("GET", "/locations/{id}/feedbacks", self._get_feedbacks_by_location)
        router.add("GET", "/locations/{id}/tables", self._get_tables_by_location_id)
        router.add(
            "GET",
            "/feedbacks/context/{reservation_id}",
            self._get_feedback_context,
        )
        router.add("POST", "/feedbacks", self._leave_feedback)

        router.add("GET", "/bookings/tables", self._get_available_tables)
        router.add("GET", "/bookings/waiter/tables", self._get_waiter_available_tables)
        router.add("POST", "/bookings/client", self._create_booking)
        router.add("GET", "/bookings/client", self._list_dashboard_bookings)
        router.add("GET", "/bookings/client/{reservation_id}", self._get_booking)
        router.add("PUT", "/bookings/client/{reservation_id}", self._update_booking)
        router.add(
            "PUT", "/bookings/waiter/{reservation_id}", self._update_waiter_booking
        )
        router.add(
            "DELETE",
            "/bookings/client/{reservation_id}/cancel",
            self._cancel_booking,
        )

        router.add("GET", "/dishes", self._get_dishes)
        router.add("GET", "/dishes/popular", self._get_popular_dishes)
        router.add("GET", "/dishes/{id}", self._get_dish_by_id)

        router.add("GET", "/customers", self._get_customers)

        router.add("GET", "/reservations/waiter", self._get_waiter_reservations)

        router.add("POST", "/orders", self._create_order)

        return router

    def _get_router(self) -> Router:
        """Lazily initialize router for tests that bypass __init__."""
        if not hasattr(self, "_router"):
            self._router = self._build_router()
        return self._router

    @staticmethod
    def _extract_access_token(event: dict) -> str:
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

    def _get_actor_context(self, event: dict) -> tuple[str, str]:
        """Return authenticated actor id and role from access token."""
        access_token = self._extract_access_token(event)
        return self._cognito_service.get_identity_from_access_token(access_token)

    @staticmethod
    def _parse_body(event: dict) -> str | Any:
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

    @staticmethod
    def _validate(model_cls, payload: dict):
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

    def _get_waiter_location(self, event: dict) -> LambdaResponse:
        """Return current waiter's assigned location id and address."""
        access_token = self._extract_access_token(event)
        response = self._user_profile_service.get_waiter_location(access_token)

        return build_response(
            response.model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_locations(self) -> LambdaResponse:
        """Return all restaurant locations for the public locations page."""
        locations: list[LocationResponse] = self._locations_service.get_locations()
        return build_response(
            [location.model_dump() for location in locations],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_customers(self, event: dict) -> LambdaResponse:
        """Return all customers for waiter-facing dashboard workflows."""
        _, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can access customers list.",
            )

        customers: list[CustomerResponse] = self._customers_service.get_customers()
        return build_response(
            [customer.model_dump(mode="json") for customer in customers],
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
        location_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
        )

        location = self._locations_service.get_location_by_id(location_id)
        if location is None:
            self._raise_location_not_found()

        return build_response(
            location.model_dump(),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_valid_slot_times_payload(self, event: dict) -> dict[str, list[str]]:
        """Return valid slot start/end times payload for a location."""
        location_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
        )

        slot_times = self._locations_service.get_valid_slot_times(location_id)
        if slot_times is None:
            self._raise_location_not_found()

        return slot_times

    def _get_valid_slot_times(self, event: dict) -> LambdaResponse:
        """Handle GET /locations/{id}/valid-slot-times."""
        slot_times = self._get_valid_slot_times_payload(event)

        return build_response(
            slot_times,
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    @staticmethod
    def _raise_location_not_found() -> None:
        """Raise standardized 404 error for missing location."""
        raise_error_response(
            HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
            ValidationErrorResponse(
                errors=[FieldError(field="id", message="Location not found")]
            ).model_dump(),
        )

    # TODO: da li je neophodno za svaki posebno da postoji _raise_x_not_found metoda? mozda treba da se centralizuje
    @staticmethod
    def _raise_dish_not_found() -> None:
        """Raise standardized 404 error for missing or invalid dish id."""
        raise_error_response(
            HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
            ValidationErrorResponse(
                errors=[FieldError(field="id", message="Dish not found")]
            ).model_dump(),
        )

    @staticmethod
    def _parse_query_params(event: dict) -> dict:
        """Extract query string parameters from API Gateway event."""
        return event.get("queryStringParameters") or {}

    @staticmethod
    def _extract_path_param(
        event: dict,
        name: str,
        fallback_position: int | None = None,
    ) -> str | None:
        """Extract path parameter by key, with optional fallback to path segment."""
        path_params = event.get("pathParameters") or {}
        if name in path_params:
            return path_params.get(name)

        if fallback_position is None:
            return None

        path = event.get("path", "")
        parts = [part for part in path.split("/") if part]
        if fallback_position < len(parts):
            return parts[fallback_position]
        return None

    @staticmethod
    def _require_uuid(
        raw_value: str | None,
        *,
        field: str,
        missing_message: str | None = None,
        invalid_message: str | None = None,
    ) -> UUID:
        """Validate and parse UUID values from path/query inputs."""
        if missing_message is None:
            missing_message = f"'{field}' is required"
        if invalid_message is None:
            invalid_message = f"'{field}' must be a valid UUID"

        normalized_value = (
            raw_value.strip() if isinstance(raw_value, str) else raw_value
        )

        if normalized_value is None or normalized_value == "":
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field=field, message=missing_message)]
                ).model_dump(),
            )

        try:
            return UUID(normalized_value)
        except (ValueError, TypeError):
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[FieldError(field=field, message=invalid_message)]
                ).model_dump(),
            )

    def _get_available_tables(self, event: dict):
        """Handle GET /bookings/tables.

        Query params:
            - location_id (required): UUID of the restaurant location.
            - date (required): Booking date in YYYY-MM-DD format.
            - guests_number (required): Minimum number of guests (1-10).
            - from_time (optional): UTC datetime filter in ISO format.
                Example: 2026-05-27T11:45:00Z.
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
                "from_time": params.get("from_time"),
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
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_waiter_available_tables(self, event: dict) -> LambdaResponse:
        """Handle GET /bookings/waiter/tables for waiter-facing availability.

        Waiters can filter by location, optional date, guest count, and a
        UTC datetime time window. The customer endpoint remains unchanged.
        """
        _, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can access this endpoint",
            )

        params = self._parse_query_params(event)
        request = self._validate(WaiterAvailableTablesRequest, params)

        response = self._table_availability_service.get_available_tables_for_waiter(
            location_id=request.location_id,
            booking_date=request.date,
            guests_number=request.guests_number,
            from_time=request.from_time,
            to_time=request.to_time,
        )

        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _create_booking(self, event: dict) -> LambdaResponse:
        """Handle POST /bookings/client — create a reservation for customer/waiter flows.

        Flow:
            1. Extract the access token and resolve the caller's identity.
                        2. Allow callers with ``UserRole.CUSTOMER`` or ``UserRole.WAITER``.
                             Customers always create under their own identity.
                             Waiters must provide ``existingCustomer``:
                                 - ``existingCustomer=true`` requires ``customerId``.
                                 - ``existingCustomer=false`` requires ``clientName``.
            3. Validate the JSON body against :class:`CreateBookingRequest`.
            4. Delegate persistence to :class:`BookingService.create_booking`.
            5. Return the saved reservation details for the UI success
               confirmation.

        """
        user_id, role = self._get_actor_context(event)
        if role not in (UserRole.CUSTOMER, UserRole.WAITER):
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only customers and waiters can create a reservation",
            )

        request: CreateBookingRequest = self._validate(
            CreateBookingRequest, self._parse_body(event)
        )

        if role == UserRole.CUSTOMER:
            if request.existing_customer is not None:
                raise_error_response(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    ValidationErrorResponse(
                        errors=[
                            FieldError(
                                field="existingCustomer",
                                message=(
                                    "existingCustomer is not allowed for customer self-booking"
                                ),
                            )
                        ]
                    ).model_dump(),
                )

            if request.customer_id is not None:
                raise_error_response(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    ValidationErrorResponse(
                        errors=[
                            FieldError(
                                field="customerId",
                                message=(
                                    "customerId is not allowed for customer self-booking"
                                ),
                            )
                        ]
                    ).model_dump(),
                )

            reservation_customer_id = user_id
            client_name = None
            creator_waiter_id = None
        else:
            if request.existing_customer is None:
                raise_error_response(
                    HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                    ValidationErrorResponse(
                        errors=[
                            FieldError(
                                field="existingCustomer",
                                message=(
                                    "Waiter booking requires existingCustomer flag"
                                ),
                            )
                        ]
                    ).model_dump(),
                )

            if request.existing_customer:
                if request.customer_id is None:
                    raise_error_response(
                        HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                        ValidationErrorResponse(
                            errors=[
                                FieldError(
                                    field="customerId",
                                    message=(
                                        "customerId is required when existingCustomer is true"
                                    ),
                                )
                            ]
                        ).model_dump(),
                    )

                if self._customer_repository.get(request.customer_id) is None:
                    raise_error_response(
                        HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                        "Customer not found",
                    )

                reservation_customer_id = request.customer_id
                client_name = None
            else:
                if request.customer_id is not None:
                    raise_error_response(
                        HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                        ValidationErrorResponse(
                            errors=[
                                FieldError(
                                    field="customerId",
                                    message=(
                                        "customerId must be omitted when existingCustomer is false"
                                    ),
                                )
                            ]
                        ).model_dump(),
                    )

                if not request.client_name:
                    raise_error_response(
                        HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                        ValidationErrorResponse(
                            errors=[
                                FieldError(
                                    field="clientName",
                                    message=(
                                        "clientName is required when existingCustomer is false"
                                    ),
                                )
                            ]
                        ).model_dump(),
                    )

                reservation_customer_id = None
                client_name = request.client_name

            creator_waiter_id = user_id

        response = self._booking_service.create_booking(
            request=request,
            customer_id=reservation_customer_id,
            client_name=client_name,
            waiter_id=creator_waiter_id,
        )

        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _list_dashboard_bookings(self, event: dict) -> LambdaResponse:
        """Handle GET /bookings/client for customer/waiter dashboard reservations."""
        user_id, role = self._get_actor_context(event)

        response = self._reservation_management_service.list_for_dashboard(
            actor_id=user_id,
            role=role,
        )
        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_booking(self, event: dict) -> LambdaResponse:
        """Handle GET /bookings/client/{reservationId}."""
        user_id, role = self._get_actor_context(event)
        reservation_id = str(
            self._require_uuid(
                self._extract_path_param(event, "reservation_id", fallback_position=2),
                field="reservationId",
            )
        )

        response = self._reservation_management_service.get_reservation(
            reservation_id=reservation_id,
            actor_id=user_id,
            role=role,
        )

        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _update_booking(self, event: dict) -> LambdaResponse:
        """Handle PUT /bookings/client/{reservationId}."""
        user_id, role = self._get_actor_context(event)
        reservation_id = str(
            self._require_uuid(
                self._extract_path_param(event, "reservation_id", fallback_position=2),
                field="reservationId",
            )
        )
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
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _update_waiter_booking(self, event: dict) -> LambdaResponse:
        """Handle PUT /bookings/waiter/{reservationId} — waiter-only status update."""
        user_id, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can access this endpoint",
            )
        reservation_id = str(
            self._require_uuid(
                self._extract_path_param(event, "reservation_id", fallback_position=2),
                field="reservationId",
            )
        )
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
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _cancel_booking(self, event: dict) -> LambdaResponse:
        """Handle PUT /bookings/client/{reservationId}/cancel."""
        user_id, role = self._get_actor_context(event)
        reservation_id = str(
            self._require_uuid(
                self._extract_path_param(event, "reservation_id", fallback_position=2),
                field="reservationId",
            )
        )

        response = self._reservation_management_service.cancel_reservation(
            reservation_id=reservation_id,
            actor_id=user_id,
            role=role,
        )

        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_waiter_reservations(self, event: dict) -> LambdaResponse:
        """Handle GET /reservations/waiter — table-filtered view for a waiter.

        Only callers with ``UserRole.WAITER`` may access this endpoint; any other
        role returns 403. The required ``date``, ``time_from`` and ``table_name``
        query parameters are validated, then reservations are returned for the
        waiter's assigned location only.

        Returns:
            A Lambda proxy response with statusCode 200 and a JSON object of the
            form ``{"reservations": [...]}``.

        """
        user_id, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can access this endpoint",
            )

        request = self._validate(
            GetWaiterReservationsRequest, self._parse_query_params(event)
        )
        response = self._reservation_management_service.list_for_waiter_table(
            waiter_id=user_id,
            date=request.date.isoformat(),
            time_from=request.time_from,
            table_name=request.table_name,
        )
        return build_response(
            response.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_dishes(self, event: dict) -> LambdaResponse:
        """Handle GET /dishes — retrieve dishes optionally filtered and sorted.

        Public endpoint; no authentication required.
        Accepts optional query parameters ``dishType``, ``sort`` and ``filter``.
        Returns 422 when an unrecognised value is supplied for any of the params.

        Returns:
            A Lambda proxy response dict with statusCode 200 and a JSON array
            of DishPreviewResponse objects, or an empty array when none match.

        """
        params = self._parse_query_params(event)
        request = self._validate(GetDishesRequest, params)
        dishes = self._dishes_service.get_all_dishes(
            dish_type=request.dishType,
            sort=request.sort,
            dietary_filter=request.dietary_filter,
        )
        return build_response(
            [dish.model_dump(mode="json") for dish in dishes],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_popular_dishes(self, event: dict) -> LambdaResponse:
        """Handle GET /dishes/popular — retrieve all popular dishes across locations.

        Returns a list of all dishes marked as popular, across all restaurant
        locations. No authentication required (public endpoint).

        Uses a DynamoDB GSI on the ``popular`` flag for O(1) lookup efficiency.

        Returns:
            A Lambda proxy response dict with statusCode 200 and a JSON array
            of DishPreviewResponse objects, or an empty array if no popular dishes exist.

        """
        dishes = self._dishes_service.get_popular_dishes()
        return build_response(
            [dish.model_dump(mode="json") for dish in dishes],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_dish_by_id(self, event: dict) -> LambdaResponse:
        """Handle GET /dishes/{id}.

        Returns a single extended dish object for the requested id.
        Returns 422 when the id is missing/invalid and 404 when dish is not found.

        """
        dish_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
        )

        dish = self._dishes_service.get_dish_by_id(dish_id)
        if dish is None:
            self._raise_dish_not_found()

        return build_response(
            dish.model_dump(mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_speciality_dishes_by_location(self, event: dict) -> LambdaResponse:
        """Handle GET /locations/{id}/speciality-dishes.

        Returns speciality dishes for the requested location only.

        """
        location_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
        )

        dishes = self._dishes_service.get_speciality_dishes_by_location(location_id)
        return build_response(
            [dish.model_dump(mode="json") for dish in dishes],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_feedbacks_by_location(self, event: dict) -> LambdaResponse:
        """Handle GET /locations/{id}/feedbacks.

        Returns feedbacks for the requested location only.

        """
        location_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
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

        sort_values = [sort_value]

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
            sort=sort_values,
            page=page,
            size=size,
        )

        if isinstance(feedback_page, dict):
            content = feedback_page.get("content", [])
            feedback_page["content"] = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in content
            ]
            feedback_page = PageFeedbackResponse.model_validate(feedback_page)

        total_pages = feedback_page.total_pages

        max_page = max(total_pages - 1, 0)
        if page > max_page:
            raise_error_response(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                ValidationErrorResponse(
                    errors=[
                        FieldError(
                            field="page",
                            message=f"Requested page {page} exceeds available pages.",
                        )
                    ]
                ).model_dump(),
            )

        return build_response(
            feedback_page.model_dump(by_alias=True, mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _get_tables_by_location_id(self, event: dict) -> LambdaResponse:
        """Return all tables for a location; restricted to waiters.

        Args:
            event: The Lambda event dict from API Gateway.

        Returns:
            A 200 response with a list of TableDTO objects.

        """
        _, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can access tables list.",
            )

        location_id = self._require_uuid(
            self._extract_path_param(event, "id", fallback_position=1),
            field="id",
        )

        tables = self._table_availability_service.get_tables_by_location_id(location_id)
        return build_response(
            [TableDTO(table_number=t.table_number).model_dump() for t in tables],
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _leave_feedback(self, event: dict) -> LambdaResponse:
        """Handle POST /feedbacks/ for customer-submitted feedback."""
        user_id, role = self._get_actor_context(event)
        if role != UserRole.CUSTOMER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only customers can leave feedback.",
            )

        request: LeaveFeedbackRequest = self._validate(
            LeaveFeedbackRequest, self._parse_body(event)
        )

        self._feedback_service.leave_feedback(request=request, customer_id=user_id)

        return build_response(
            LeaveFeedbackResponse(message="Feedback has been created.").model_dump(),
            code=HttpStatusCode.RESPONSE_CREATED_CODE,
        )

    def _get_feedback_context(self, event: dict) -> LambdaResponse:
        """Handle GET /feedbacks/context/{reservation_id} for feedback modal data."""
        user_id, role = self._get_actor_context(event)
        if role != UserRole.CUSTOMER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only customers can access feedback context.",
            )

        reservation_id = str(
            self._require_uuid(
                self._extract_path_param(event, "reservation_id", fallback_position=3),
                field="reservation_id",
            )
        )

        response = self._feedback_service.get_feedback_context(
            reservation_id=reservation_id,
            customer_id=user_id,
        )

        return build_response(
            response.model_dump(mode="json"),
            code=HttpStatusCode.RESPONSE_OK_CODE,
        )

    def _create_order(self, event: dict) -> LambdaResponse:
        """Handle POST /orders — create an order for a reservation.

        Only callers with ``UserRole.WAITER`` may access this endpoint. The
        waiter must be the one assigned to the target reservation; any mismatch
        returns 403. Each ``dishId`` in the item list must resolve to an
        existing dish, otherwise 404 is returned.

        Returns:
            A Lambda proxy response with statusCode 201 and a JSON object
            containing ``orderId`` and ``reservationId``.

        """
        waiter_id, role = self._get_actor_context(event)
        if role != UserRole.WAITER:
            raise_error_response(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Only waiters can create orders.",
            )

        request = self._validate(CreateOrderRequest, self._parse_body(event))
        response = self._order_service.create_order(
            waiter_id=UUID(waiter_id), request=request
        )
        return build_response(
            response.model_dump(by_alias=True),
            code=HttpStatusCode.RESPONSE_CREATED_CODE,
        )


HANDLER = ApiHandler()


def lambda_handler(event: dict, context: Any) -> dict | None:
    """Entry point invoked by AWS Lambda."""
    return HANDLER.lambda_handler(event=event, context=context)

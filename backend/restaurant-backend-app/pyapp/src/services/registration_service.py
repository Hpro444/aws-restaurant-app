"""Service layer for user registration with automatic role assignment."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.user import Customer, Waiter
from dto.sign_up import SignUpRequest
from enums.user_role import UserRole
from pydantic import SecretStr
from repositories.customer_repository import CustomerRepository
from repositories.waiter_emails_repository import WaiterEmailsRepository
from repositories.waiter_repository import WaiterRepository

from services.cognito_service import CognitoService


class RegistrationService:
    """Orchestrates user registration with automatic role determination.

    Checks the waiter-emails allow-list for waiter role assignment: if the
    email exists in that table, the user is registered as a Waiter with the
    associated restaurant_id; otherwise, they are registered as a Customer.

    Persists the user to the appropriate DynamoDB table after Cognito registration.
    """

    def __init__(
        self,
        settings: AppConfig | None = None,
        cognito_service: CognitoService | None = None,
    ) -> None:
        """Initialise dependencies.

        Args:
            settings: Application config; a fresh instance is created when omitted.
            cognito_service: Optional injected Cognito service instance.

        """
        self._settings = settings or AppConfig()
        self._cognito_service = cognito_service or CognitoService()
        self._waiter_emails_repo = WaiterEmailsRepository(self._settings)
        self._waiter_repo = WaiterRepository(self._settings)
        self._customer_repo = CustomerRepository(self._settings)

    def register_user(self, request: SignUpRequest) -> str:
        """Register a user with automatic role assignment and persistence.

        Checks the waiter-emails list to determine if the user should be
        registered as a Waiter (with location_id) or as a Customer. Registers
        the user in Cognito with the resolved role, then persists the user
        profile to the appropriate DynamoDB table.

        Args:
            request: Validated sign-up request with first/last name, email, password.

        Returns:
            The Cognito ``sub`` UUID for the newly created user.

        Raises:
            ApplicationException: 409 if email already exists, 500 for any error.

        """
        logger.info("Starting user registration", email=request.email)

        # Resolve role and restaurant_id using the waiter emails table.
        role = UserRole.CUSTOMER
        location_id: UUID | None = None

        try:
            waiter_email = self._waiter_emails_repo.get(request.email)
            if waiter_email:
                role = UserRole.WAITER
                location_id = waiter_email.location_id
                logger.info(
                    "Email found in waiter emails table, assigning waiter role",
                    email=request.email,
                    location_id=location_id,
                )
        except Exception as exc:
            logger.error("Failed to check waiter emails table", error=str(exc))
            raise

        # Register user in Cognito with resolved role.
        user_id = self._cognito_service.register_user(
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            password=SecretStr(request.password.get_secret_value()),
            role=role,
        )
        logger.info("User registered in Cognito", sub=user_id, role=role.value)

        # Persist to DynamoDB with resolved role.
        try:
            if role == UserRole.WAITER and location_id:
                waiter = Waiter(
                    id=UUID(user_id),
                    fname=request.first_name,
                    lname=request.last_name,
                    email=request.email,
                    image_url="",
                    restaurant_id=location_id,
                )
                self._waiter_repo.create(waiter)
                logger.info("Waiter persisted to DynamoDB", sub=user_id)
            else:
                customer = Customer(
                    id=UUID(user_id),
                    fname=request.first_name,
                    lname=request.last_name,
                    email=request.email,
                    image_url="",
                )
                self._customer_repo.create(customer)
                logger.info("Customer persisted to DynamoDB", sub=user_id)
        except Exception as exc:
            logger.error(
                "Failed to persist user to DynamoDB",
                sub=user_id,
                error=str(exc),
            )
            raise

        return user_id

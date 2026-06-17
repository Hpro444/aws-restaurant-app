"""Service layer for user registration with automatic role assignment."""

from __future__ import annotations

from uuid import UUID

from commons.app_config import AppConfig
from commons.log_helper import logger
from domain.admin import Admin
from domain.user import Customer, Waiter
from dto.sign_up import SignUpRequest
from enums import UserRole
from pydantic import SecretStr
from repositories.admin_emails_repository import AdminEmailsRepository
from repositories.admin_repository import AdminRepository
from repositories.customer_repository import CustomerRepository
from repositories.waiter_emails_repository import WaiterEmailsRepository
from repositories.waiter_repository import WaiterRepository

from services.cognito_service import CognitoService


class RegistrationService:
    """Orchestrates user registration with automatic role determination.

    Checks the admin-emails allow-list first, then the waiter-emails allow-list.
    If the email exists in admin-emails, the user is registered as an Admin.
    If the email exists in waiter-emails, the user is registered as a Waiter
    with the associated location_id. Otherwise, they are registered as a Customer.

    Persists the user to the appropriate DynamoDB table after Cognito registration.
    """

    def __init__(
        self,
        cognito_service: CognitoService | None = None,
        waiter_repository: WaiterRepository | None = None,
        customer_repository: CustomerRepository | None = None,
        waiter_emails_repository: WaiterEmailsRepository | None = None,
        admin_repository: AdminRepository | None = None,
        admin_emails_repository: AdminEmailsRepository | None = None,
        settings: AppConfig | None = None,
    ) -> None:
        """Initialize dependencies.

        Args:
            cognito_service: Cognito service for user management.
            waiter_repository: Repository for waiter profiles.
            customer_repository: Repository for customer profiles.
            waiter_emails_repository: Repository for waiter email allow-list.
            admin_repository: Repository for admin profiles.
            admin_emails_repository: Repository for admin email allow-list.
            settings: Application configuration; a fresh instance is created when omitted.

        """
        self._cognito_service = cognito_service or CognitoService()
        self._waiter_repo = waiter_repository or WaiterRepository()
        self._customer_repo = customer_repository or CustomerRepository()
        self._waiter_emails_repo = waiter_emails_repository or WaiterEmailsRepository()
        self._admin_repo = admin_repository or AdminRepository()
        self._admin_emails_repo = admin_emails_repository or AdminEmailsRepository()

    def _persist_user(
        self,
        user_id: str,
        request: SignUpRequest,
        role: UserRole,
        location_id: UUID | None,
    ) -> None:
        """Build the role-specific domain model from the Cognito sub and persist it to DynamoDB.

        Args:
            user_id: The Cognito ``sub`` UUID string returned by Cognito after registration.
            request: The original sign-up request containing name and email.
            role: Resolved role that determines which table (admin/waiter/customer) is written to.
            location_id: Required for waiters; ignored for admins and customers.

        """
        common = {
            "id": UUID(user_id),
            "fname": request.first_name,
            "lname": request.last_name,
            "email": request.email,
            "image_url": "",
        }

        if role == UserRole.ADMIN:
            self._admin_repo.create(Admin(**common))
            logger.info("Admin persisted to DynamoDB", sub=user_id)
            return

        if role == UserRole.WAITER and location_id:
            self._waiter_repo.create(Waiter(**common, location_id=location_id))
            logger.info("Waiter persisted to DynamoDB", sub=user_id)
            return

        self._customer_repo.create(Customer(**common))
        logger.info("Customer persisted to DynamoDB", sub=user_id)

    def register_user(self, request: SignUpRequest) -> None:
        """Register a user with automatic role assignment and persistence.

        Checks the waiter-emails list to determine if the user should be
        registered as a Waiter (with location_id) or as a Customer. Registers
        the user in Cognito with the resolved role, then persists the user
        profile to the appropriate DynamoDB table.

        Args:
            request: Validated sign-up request with first/last name, email, password.

        Raises:
            ApplicationException: 409 if email already exists, 500 for any error.

        """
        logger.info("Starting user registration", email=request.email)

        # Resolve role: admin-emails checked first, then waiter-emails, then customer.
        role = UserRole.CUSTOMER
        location_id: UUID | None = None

        try:
            admin_email = self._admin_emails_repo.get(request.email)
            if admin_email:
                role = UserRole.ADMIN
                logger.info(
                    "Email found in admin emails table, assigning admin role",
                    email=request.email,
                )
            else:
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
            logger.error("Failed to check role emails tables", error=str(exc))
            raise

        # Register user in Cognito with resolved role.
        user_id = self._cognito_service.register_user(
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            password=SecretStr(request.password.get_secret_value()),
            role=role,
        )
        logger.info("User registered in Cognito", sub=user_id, role=role)

        # Persist to DynamoDB with resolved role.
        try:
            self._persist_user(user_id, request, role, location_id)
        except Exception as exc:
            logger.error(
                "Failed to persist user to DynamoDB",
                sub=user_id,
                error=str(exc),
            )
            raise

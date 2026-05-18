"""Service for managing user profiles."""

from uuid import UUID

from commons.exceptions import ApplicationException
from commons.log_helper import logger
from enums.http_status_code import HttpStatusCode
from enums.user_role import UserRole
from repositories.customer_repository import CustomerRepository
from repositories.waiter_repository import WaiterRepository

from services.cognito_service import CognitoService


class UserProfileService:
    """Handles user profile retrieval based on access tokens."""

    def __init__(
        self,
        cognito_service: CognitoService | None = None,
        customer_repository: CustomerRepository | None = None,
        waiter_repository: WaiterRepository | None = None,
    ) -> None:
        """Initialize dependencies, creating them if not provided."""
        self._cognito_service = cognito_service or CognitoService()
        self._customer_repository = customer_repository or CustomerRepository()
        self._waiter_repository = waiter_repository or WaiterRepository()

    def get_user_profile(self, access_token: str):
        """Retrieve the user profile based on the access token.

        Args:
            access_token: The JWT access token from the Authorization header.

        Returns:
            The user profile object.

        Raises:
            ApplicationException: 401 for invalid token, 404 for profile not found.

        """
        # Decode and validate the token
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )

        # Query the appropriate repository based on the role
        if role == UserRole.CUSTOMER.value:
            user = self._customer_repository.get(UUID(user_id))
        elif role == UserRole.WAITER.value:
            user = self._waiter_repository.get(UUID(user_id))
        # TODO: Extend with Admin role
        else:
            logger.info("Unsupported role", role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                content="Role is not supported for this endpoint",
            )

        if user is None:
            logger.info("User profile not found", user_id=user_id, role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Profile not found",
            )

        return user

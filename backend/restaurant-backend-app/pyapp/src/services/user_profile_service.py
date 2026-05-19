"""Service for managing user profiles."""

from uuid import UUID

from commons.exceptions import ApplicationException
from commons.log_helper import logger
from domain.admin import Admin
from domain.user import Customer, Waiter
from dto.user_profile import UpdateProfileRequest
from enums.http_status_code import HttpStatusCode
from enums.user_role import UserRole
from repositories.admin_repository import AdminRepository
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
        admin_repository: AdminRepository | None = None,
    ) -> None:
        """Initialize dependencies, creating them if not provided."""
        self._cognito_service = cognito_service or CognitoService()
        self._customer_repository = customer_repository or CustomerRepository()
        self._waiter_repository = waiter_repository or WaiterRepository()
        self._admin_repository = admin_repository or AdminRepository()

    def get_user_profile(self, access_token: str):
        """Retrieve the user profile based on the access token.

        Args:
            access_token: The JWT access token from the Authorization header.

        Returns:
            The user profile object.

        Raises:
            ApplicationException: 401 for invalid token, 404 for profile not found.

        """
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )

        if role == UserRole.CUSTOMER:
            user = self._customer_repository.get(UUID(user_id))
        elif role == UserRole.WAITER:
            user = self._waiter_repository.get(UUID(user_id))
        elif role == UserRole.ADMIN:
            user = self._admin_repository.get(UUID(user_id))
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

    def update_user_profile(self, access_token: str, request: UpdateProfileRequest):
        """Update the authenticated user's profile fields and persist the change.

        Only ``first_name``, ``last_name``, and ``image_url`` can be changed.
        ``email``, ``role``, and role-specific fields (e.g. ``location_id`` for
        Waiter) are preserved from the existing record.

        Args:
            access_token: The JWT access token from the Authorization header.
            request: Validated update payload with new field values.

        Returns:
            The updated user domain object.

        Raises:
            ApplicationException: 401 for invalid token, 403 for unsupported role,
                404 when the profile record does not exist.

        """
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )

        if role == UserRole.CUSTOMER:
            existing = self._customer_repository.get(UUID(user_id))
        elif role == UserRole.WAITER:
            existing = self._waiter_repository.get(UUID(user_id))
        elif role == UserRole.ADMIN:
            existing = self._admin_repository.get(UUID(user_id))
        else:
            logger.info("Unsupported role for profile update", role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                content="Role is not supported for this endpoint",
            )

        if existing is None:
            logger.info("User profile not found for update", user_id=user_id, role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Profile not found",
            )

        if role == UserRole.CUSTOMER:
            updated = Customer(
                id=existing.id,
                fname=request.first_name,
                lname=request.last_name,
                email=existing.email,
                image_url=request.image_url,
            )
            self._customer_repository.update(updated)
        elif role == UserRole.WAITER:
            updated = Waiter(
                id=existing.id,
                fname=request.first_name,
                lname=request.last_name,
                email=existing.email,
                image_url=request.image_url,
                location_id=existing.location_id,
            )
            self._waiter_repository.update(updated)
        else:
            updated = Admin(
                id=existing.id,
                fname=request.first_name,
                lname=request.last_name,
                email=existing.email,
                image_url=request.image_url,
            )
            self._admin_repository.update(updated)

        logger.info("Profile updated", user_id=user_id, role=role)
        return updated

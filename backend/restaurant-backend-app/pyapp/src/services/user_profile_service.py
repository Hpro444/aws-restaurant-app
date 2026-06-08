"""Service for managing user profiles."""

from uuid import UUID

from commons.exceptions import ApplicationException
from commons.log_helper import logger
from domain.admin import Admin
from domain.user import Customer, Waiter
from dto.locations import LocationAddressResponse
from dto.user_profile import UpdateProfileRequest
from enums.http_status_code import HttpStatusCode
from enums.user_role import UserRole
from repositories.admin_repository import AdminRepository
from repositories.customer_repository import CustomerRepository
from repositories.location_repository import LocationRepository
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
        location_repository: LocationRepository | None = None,
    ) -> None:
        """Initialize dependencies, creating them if not provided."""
        self._cognito_service = cognito_service or CognitoService()
        self._customer_repository = customer_repository or CustomerRepository()
        self._waiter_repository = waiter_repository or WaiterRepository()
        self._admin_repository = admin_repository or AdminRepository()
        self._location_repository = location_repository or LocationRepository()
        self._repo_by_role = {
            UserRole.CUSTOMER: self._customer_repository,
            UserRole.WAITER: self._waiter_repository,
            UserRole.ADMIN: self._admin_repository,
        }

    def get_user_profile(self, access_token: str):
        """Return authenticated user's profile."""
        _, _, _, user = self._resolve_profile_context(
            access_token=access_token,
            unsupported_role_message="Unsupported role",
            not_found_message="User profile not found",
        )
        return user

    def update_user_profile(self, access_token: str, request: UpdateProfileRequest):
        """Update authenticated user's profile and persist changes."""
        user_id, role, repository, existing = self._resolve_profile_context(
            access_token=access_token,
            unsupported_role_message="Unsupported role for profile update",
            not_found_message="User profile not found for update",
        )

        updated = self._build_updated_profile(role, existing, request)
        repository.update(updated)

        logger.info("Profile updated", user_id=user_id, role=role)
        return updated

    def get_waiter_location(self, access_token: str) -> LocationAddressResponse:
        """Return authenticated waiter's assigned location id and address."""
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        # TODO: ovo mozemo da poboljsamo dodavanjem neke anotacije ili nekakvom centralizacijom na nivou app
        if role != UserRole.WAITER:
            logger.info("Unsupported role for waiter location", role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                content="Only waiters can access this endpoint",
            )

        waiter = self._waiter_repository.get(UUID(user_id))
        if waiter is None:
            logger.info("Waiter profile not found", user_id=user_id)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Profile not found",
            )

        location = self._location_repository.get(waiter.location_id)
        if location is None:
            logger.info(
                "Waiter location not found",
                user_id=user_id,
                location_id=str(waiter.location_id),
            )
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Waiter location not found",
            )

        return LocationAddressResponse(
            location_id=str(location.id),
            location_address=location.address,
        )

    def _resolve_profile_context(
        self,
        access_token: str,
        unsupported_role_message: str,
        not_found_message: str,
    ):
        """Resolve identity, role repository, and profile row or raise endpoint errors."""
        user_id, role = self._cognito_service.get_identity_from_access_token(
            access_token
        )
        repository = self._repo_by_role.get(role)
        if repository is None:
            logger.info(unsupported_role_message, role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                content="Role is not supported for this endpoint",
            )

        profile = repository.get(UUID(user_id))
        if profile is None:
            logger.info(not_found_message, user_id=user_id, role=role)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                content="Profile not found",
            )

        return user_id, role, repository, profile

    @staticmethod
    def _build_updated_profile(role: str, existing, request: UpdateProfileRequest):
        """Build updated domain model per role using shared profile fields."""
        common_kwargs = {
            "id": existing.id,
            "fname": request.first_name,
            "lname": request.last_name,
            "email": existing.email,
            "image_url": request.image_url,
        }
        if role == UserRole.CUSTOMER:
            return Customer(**common_kwargs)
        if role == UserRole.WAITER:
            return Waiter(**common_kwargs, location_id=existing.location_id)
        return Admin(**common_kwargs)

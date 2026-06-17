"""Service layer for AWS Cognito user management."""

from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.jwt_decoder import decode_access_token_payload
from commons.log_helper import logger
from domain.auth_result import AuthResult
from enums import HttpStatusCode, UserRole
from pydantic import SecretStr

from services.login_attempts_service import LoginAttemptsService


class CognitoService:
    """Cognito user-management service."""

    def __init__(
        self,
        settings: AppConfig | None = None,
        client: object | None = None,
        login_attempts_service: LoginAttemptsService | None = None,
    ) -> None:
        """Initialize settings, Cognito client and login-attempts service."""
        self._settings = settings or AppConfig()
        self._client = client or boto3.client(
            "cognito-idp", region_name=self._settings.aws_region
        )
        self._pool_id: str | None = None
        self._client_id: str | None = None
        self._login_attempts_service = login_attempts_service or LoginAttemptsService(
            self._settings
        )

    def _resolve_pool_id(self) -> str:
        """Resolve and cache Cognito User Pool ID by configured pool name."""
        if self._pool_id:
            logger.debug("Pool ID cache hit", pool_id=self._pool_id)
            return self._pool_id

        pool_name = self._settings.user_pool_name
        logger.info("Resolving pool ID", pool_name=pool_name)
        paginator_token = None

        while True:
            params = {"MaxResults": self._settings.cognito_max_results}
            if paginator_token:
                params["NextToken"] = paginator_token

            response = self._client.list_user_pools(**params)

            for pool in response.get("UserPools", []):
                if pool_name in pool["Name"]:
                    self._pool_id = pool["Id"]
                    logger.info(
                        "Resolved pool", name=pool["Name"], pool_id=self._pool_id
                    )
                    self._ensure_groups(self._pool_id)
                    return self._pool_id

            paginator_token = response.get("NextToken")
            if not paginator_token:
                break

        logger.error("No user pool found", pool_name=pool_name)
        raise ApplicationException(
            code=500, content=f"Cognito user pool containing '{pool_name}' not found"
        )

    _GROUP_DEFINITIONS: tuple[tuple[str, str, int], ...] = (
        ("Admin", "Administrators group", 1),
        ("Waiter", "Waiters group", 5),
        ("Customer", "Regular users group", 10),
    )
    _REGISTRATION_FAILURE_MESSAGE = {
        "message": "Registration failed due to a server error, please try again later"
    }

    @staticmethod
    def _raise_with_cause(code: int, content, exc: Exception) -> None:
        """Raise ApplicationException preserving original cause."""
        raise ApplicationException(code=code, content=content) from exc

    @staticmethod
    def _raise_invalid_access_token(exc: Exception | None = None) -> None:
        """Raise the standard 401 error for malformed/expired access tokens."""
        if exc is None:
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                content="Invalid or expired access token",
            )
        raise ApplicationException(
            code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
            content="Invalid or expired access token",
        ) from exc

    def _ensure_groups(self, pool_id: str) -> None:
        """Create missing Cognito groups from the configured group definitions."""
        logger.info("Ensuring groups exist", pool_id=pool_id)
        try:
            existing = {
                g["GroupName"]
                for g in self._client.list_groups(UserPoolId=pool_id).get("Groups", [])
            }
        except ClientError as exc:
            logger.error("list_groups failed", error=str(exc))
            return

        logger.debug("Existing groups", groups=existing)
        for name, description, precedence in self._GROUP_DEFINITIONS:
            if name in existing:
                logger.debug("Group already exists, skipping", group=name)
                continue
            try:
                self._client.create_group(
                    UserPoolId=pool_id,
                    GroupName=name,
                    Description=description,
                    Precedence=precedence,
                )
                logger.info("Created Cognito group", group=name)
            except ClientError as exc:
                logger.error("create_group failed", group=name, error=str(exc))

    def _resolve_client_id(self, pool_id: str) -> str:
        """Resolve and cache app client ID for the given pool."""
        if self._client_id:
            logger.debug("Client ID cache hit", client_id=self._client_id)
            return self._client_id

        logger.info("Resolving app client ID", pool_id=pool_id)
        try:
            response = self._client.list_user_pool_clients(
                UserPoolId=pool_id, MaxResults=10
            )
        except ClientError as exc:
            logger.error("list_user_pool_clients failed", error=str(exc))
            raise ApplicationException(
                code=500, content="Failed to resolve Cognito app client"
            ) from exc

        clients = response.get("UserPoolClients", [])
        if not clients:
            logger.error("No app clients found", pool_id=pool_id)
            raise ApplicationException(
                code=500, content="No Cognito app client found for pool"
            )
        self._client_id = clients[0]["ClientId"]
        logger.info(
            "Resolved client",
            name=clients[0].get("ClientName"),
            client_id=self._client_id,
        )
        return self._client_id

    def register_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: SecretStr,
        role: UserRole = UserRole.CUSTOMER,
    ) -> str:
        """Create user, set permanent password, assign role group, and return sub."""
        logger.info("Registering user", email=email, role=role)
        pool_id = self._resolve_pool_id()

        try:
            response = self._client.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:first_name", "Value": first_name},
                    {"Name": "custom:last_name", "Value": last_name},
                ],
                MessageAction="SUPPRESS",
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "UsernameExistsException":
                logger.info("Registration rejected, email already exists", email=email)
                self._raise_with_cause(
                    code=409,
                    content={
                        "message": "An account with this email address already exists"
                    },
                    exc=exc,
                )
            logger.error("admin_create_user failed", error_code=code, error=str(exc))
            self._raise_with_cause(
                code=500,
                content=self._REGISTRATION_FAILURE_MESSAGE,
                exc=exc,
            )

        user_id = next(
            attr["Value"]
            for attr in response["User"]["Attributes"]
            if attr["Name"] == "sub"
        )
        logger.info("User created", sub=user_id, status=response["User"]["UserStatus"])

        try:
            self._client.admin_set_user_password(
                UserPoolId=pool_id,
                Username=email,
                Password=password.get_secret_value(),
                Permanent=True,
            )
            logger.info("Password set permanently", email=email)
        except ClientError as exc:
            logger.error(
                "admin_set_user_password failed",
                error_code=exc.response["Error"]["Code"],
                error=str(exc),
            )
            self._raise_with_cause(
                code=500,
                content=self._REGISTRATION_FAILURE_MESSAGE,
                exc=exc,
            )

        try:
            self._client.admin_add_user_to_group(
                UserPoolId=pool_id, Username=email, GroupName=role
            )
            logger.info("Assigned user to group", email=email, group=role)
        except ClientError as exc:
            logger.error(
                "admin_add_user_to_group failed",
                error_code=exc.response["Error"]["Code"],
                error=str(exc),
            )
            self._raise_with_cause(
                code=500,
                content=self._REGISTRATION_FAILURE_MESSAGE,
                exc=exc,
            )

        return user_id

    def authenticate_user(self, email: str, password: SecretStr) -> AuthResult:
        """Authenticate user with lockout enforcement and return tokens and role."""
        logger.info("Authenticating user", email=email)

        lockout_until = self._login_attempts_service.get_lockout_until(email)
        if lockout_until is not None:
            logger.info("Account is locked", email=email, lockout_until=lockout_until)
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_LOCKED_CODE,
                content={
                    "message": "Account locked due to too many failed login attempts.",
                    "lockout_until": lockout_until,
                },
            )

        pool_id = self._resolve_pool_id()
        client_id = self._resolve_client_id(pool_id)

        try:
            auth_response = self._client.initiate_auth(
                ClientId=client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password.get_secret_value(),
                },
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("NotAuthorizedException", "UserNotFoundException"):
                logger.info("Auth rejected, invalid credentials", error_code=error_code)
                new_count, lockout_until = (
                    self._login_attempts_service.increment_failed_attempts(email)
                )
                remaining = self._login_attempts_service.max_attempts - new_count
                if lockout_until is not None:
                    self._raise_with_cause(
                        code=HttpStatusCode.RESPONSE_LOCKED_CODE,
                        content={
                            "message": "Your account is temporarily locked due to multiple failed login attempts. Please try again later.",
                            "lockout_until": lockout_until,
                        },
                        exc=exc,
                    )
                if remaining == 1:
                    self._raise_with_cause(
                        code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                        content={
                            "message": "Invalid credentials. You have 1 attempt remaining before your account is temporarily locked.",
                            "remaining_attempts": 1,
                        },
                        exc=exc,
                    )
                self._raise_with_cause(
                    code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                    content={
                        "message": "Incorrect email or password. Try again or create an account."
                    },
                    exc=exc,
                )
            logger.error("initiate_auth failed", error_code=error_code, error=str(exc))
            self._raise_with_cause(
                code=500,
                content="Authentication failed",
                exc=exc,
            )

        access_token = auth_response["AuthenticationResult"]["AccessToken"]
        refresh_token = auth_response["AuthenticationResult"]["RefreshToken"]
        logger.info("Cognito auth successful", email=email)

        try:
            user_response = self._client.admin_get_user(
                UserPoolId=pool_id, Username=email
            )
        except ClientError as exc:
            logger.error(
                "admin_get_user failed",
                error_code=exc.response["Error"]["Code"],
                error=str(exc),
            )
            self._raise_with_cause(
                code=500,
                content="Authentication failed",
                exc=exc,
            )

        attrs = {
            attr["Name"]: attr["Value"] for attr in user_response["UserAttributes"]
        }
        first_name = attrs.get("custom:first_name", "")
        last_name = attrs.get("custom:last_name", "")
        logger.debug(
            "Fetched user attributes",
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        try:
            groups_response = self._client.admin_list_groups_for_user(
                UserPoolId=pool_id, Username=email
            )
        except ClientError as exc:
            logger.error(
                "admin_list_groups_for_user failed",
                error_code=exc.response["Error"]["Code"],
                error=str(exc),
            )
            self._raise_with_cause(
                code=500,
                content="Authentication failed",
                exc=exc,
            )

        groups = groups_response.get("Groups", [])
        role = groups[0]["GroupName"] if groups else ""
        logger.info("User authenticated", email=email, role=role)

        self._login_attempts_service.reset_attempts(email)

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            username=f"{first_name} {last_name}".strip(),
            role=role,
        )

    def refresh_tokens(self, refresh_token: str) -> str:
        """Exchange refresh token for a new access token."""
        logger.info("Refreshing tokens")
        pool_id = self._resolve_pool_id()
        client_id = self._resolve_client_id(pool_id)

        try:
            response = self._client.initiate_auth(
                ClientId=client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("NotAuthorizedException", "UserNotFoundException"):
                logger.info("Token refresh rejected", error_code=error_code)
                self._raise_with_cause(
                    code=401,
                    content="Invalid or expired refresh token",
                    exc=exc,
                )
            logger.error("Token refresh failed", error_code=error_code, error=str(exc))
            self._raise_with_cause(
                code=500,
                content="Token refresh failed",
                exc=exc,
            )

        access_token = response["AuthenticationResult"]["AccessToken"]
        logger.info("Token refresh successful")
        return access_token

    def logout_user(self, refresh_token: str) -> None:
        """Revoke refresh token via Cognito."""
        logger.info("Revoking refresh token")
        pool_id = self._resolve_pool_id()
        client_id = self._resolve_client_id(pool_id)

        try:
            self._client.revoke_token(Token=refresh_token, ClientId=client_id)
            logger.info("Token revoked successfully")
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("NotAuthorizedException", "TokenExpiredException"):
                logger.info("Token revocation rejected", error_code=error_code)
                self._raise_with_cause(
                    code=401,
                    content="Invalid or expired token",
                    exc=exc,
                )
            logger.error("revoke_token failed", error_code=error_code, error=str(exc))
            self._raise_with_cause(
                code=500,
                content="Logout failed",
                exc=exc,
            )

    def get_identity_from_access_token(self, access_token: str) -> tuple[str, UserRole]:
        """Validate the access token and return (user_id, role) extracted from claims."""
        try:
            self._client.get_user(AccessToken=access_token)
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            error_message = exc.response.get("Error", {}).get("Message", "")
            if error_code in (
                "NotAuthorizedException",
                "InvalidParameterException",
                "ResourceNotFoundException",
            ):
                if error_code == "InvalidParameterException" and (
                    "Authorization header" in error_message
                    or "Invalid key=value pair" in error_message
                ):
                    raise ApplicationException(
                        code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                        content=(
                            "Authorization token format is invalid. "
                            "Use 'Bearer <access_token>' and sign in again if needed."
                        ),
                    ) from exc
                self._raise_invalid_access_token(exc)
            logger.error("get_user failed", error_code=error_code, error=str(exc))
            self._raise_with_cause(
                code=HttpStatusCode.RESPONSE_INTERNAL_SERVER_ERROR,
                content="Failed to validate access token",
                exc=exc,
            )

        claims = decode_access_token_payload(access_token)
        if claims.get("token_use") != "access":
            self._raise_invalid_access_token()

        sub = claims.get("sub")
        if not isinstance(sub, str):
            self._raise_invalid_access_token()

        try:
            UUID(sub)
        except ValueError as exc:
            self._raise_invalid_access_token(exc)

        groups = claims.get("cognito:groups", [])
        if not isinstance(groups, list):
            groups = [groups] if isinstance(groups, str) else []

        for role in UserRole:
            if role in groups:
                return sub, role

        raise ApplicationException(
            code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
            content="Role is not supported for this endpoint",
        )

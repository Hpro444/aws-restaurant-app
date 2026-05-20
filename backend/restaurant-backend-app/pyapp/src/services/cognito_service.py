"""Service layer for AWS Cognito user management."""

from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.jwt_decoder import decode_access_token_payload
from commons.log_helper import logger
from domain.auth_result import AuthResult
from enums.http_status_code import HttpStatusCode
from enums.user_role import UserRole
from pydantic import SecretStr

from services.login_attempts_service import LoginAttemptsService


class CognitoService:
    """Wraps boto3 Cognito IdP calls for user registration and authentication."""

    def __init__(self) -> None:
        """Initialise settings, boto3 Cognito client, pool ID cache, and login-attempts service."""
        self._settings = AppConfig()
        self._client = boto3.client(
            "cognito-idp", region_name=self._settings.aws_region
        )
        self._pool_id: str | None = None
        self._client_id: str | None = None
        self._login_attempts_service = LoginAttemptsService(self._settings)

    def _resolve_pool_id(self) -> str:
        """Return the Cognito User Pool ID, resolving it by name on first call.

        Paginates list_user_pools until a pool whose Name contains the value
        of the USER_POOL_NAME environment variable is found, then caches the
        result for the lifetime of the Lambda execution context.

        Raises:
            ApplicationException: 500 if the pool cannot be found.

        """
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

    def _ensure_groups(self, pool_id: str) -> None:
        """Create any missing Cognito user pool groups defined in _GROUP_DEFINITIONS.

        Idempotent — existing groups are left untouched.
        """
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
        """Return the app client ID for the given pool, resolving it on first call.

        Raises:
            ApplicationException: 500 if no client is found for the pool.

        """
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
        """Create a confirmed user in Cognito, assign them to a group, and return their sub.

        Creates the user via admin_create_user (FORCE_CHANGE_PASSWORD state), then
        immediately confirms them with admin_set_user_password (Permanent=True).
        Role is managed via Cognito Groups. The plaintext password is never logged.

        Args:
            first_name: User's given name.
            last_name: User's family name.
            email: User's email address, used as the Cognito username.
            password: Plaintext password wrapped in SecretStr; hashed by Cognito on storage.
            role: Role to assign via group membership; defaults to UserRole.CUSTOMER.

        Returns:
            The Cognito `sub` UUID for the newly created user.

        Raises:
            ApplicationException: 409 if the email is already registered,
                500 for any other Cognito error.

        """
        logger.info("Registering user", email=email, role=role.value)
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
                raise ApplicationException(
                    code=409, content="Registration failed"
                ) from exc
            logger.error("admin_create_user failed", error_code=code, error=str(exc))
            raise ApplicationException(
                code=500, content="Failed to create user"
            ) from exc

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
            raise ApplicationException(
                code=500, content="Failed to confirm user account"
            ) from exc

        try:
            self._client.admin_add_user_to_group(
                UserPoolId=pool_id, Username=email, GroupName=role.value
            )
            logger.info("Assigned user to group", email=email, group=role.value)
        except ClientError as exc:
            logger.error(
                "admin_add_user_to_group failed",
                error_code=exc.response["Error"]["Code"],
                error=str(exc),
            )
            raise ApplicationException(
                code=500, content="Failed to assign user role"
            ) from exc

        return user_id

    def authenticate_user(self, email: str, password: SecretStr) -> AuthResult:
        """Authenticate a user via Cognito, enforcing per-email lockout, and return tokens.

        Checks the login-attempts table before calling Cognito. On failure, increments
        the attempt counter; the 4th failure adds ``remaining_attempts`` to the error,
        and the 5th locks the account for 15 minutes (423). Both "user not found" and
        "wrong password" are intentionally indistinguishable to prevent user enumeration.
        A successful login resets the attempt counter.

        Args:
            email: Normalised user email (already lowercased/trimmed by the DTO).
            password: Plaintext password provided by the caller.

        Returns:
            AuthResult with Cognito's AccessToken, the user's full name, and role.

        Raises:
            ApplicationException: 401 for invalid credentials, 423 when the account is
                locked, 500 for unexpected Cognito errors.

        """
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
                    raise ApplicationException(
                        code=HttpStatusCode.RESPONSE_LOCKED_CODE,
                        content={
                            "message": "Account locked due to too many failed login attempts.",
                            "lockout_until": lockout_until,
                        },
                    ) from exc
                if remaining == 1:
                    raise ApplicationException(
                        code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                        content={
                            "message": "Invalid credentials. You have 1 attempt remaining before your account is temporarily locked.",
                            "remaining_attempts": 1,
                        },
                    ) from exc
                raise ApplicationException(
                    code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                    content={
                        "message": "Incorrect email or password. Try again or create an account."
                    },
                ) from exc
            logger.error("initiate_auth failed", error_code=error_code, error=str(exc))
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

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
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

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
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

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
        """Exchange a refresh token for a new access token.

        Args:
            refresh_token: The Cognito refresh token issued at sign-in.

        Returns:
            A new AccessToken string.

        Raises:
            ApplicationException: 401 if the refresh token is expired or invalid;
                500 for unexpected Cognito errors.

        """
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
                raise ApplicationException(
                    code=401, content="Invalid or expired refresh token"
                ) from exc
            logger.error("Token refresh failed", error_code=error_code, error=str(exc))
            raise ApplicationException(
                code=500, content="Token refresh failed"
            ) from exc

        access_token = response["AuthenticationResult"]["AccessToken"]
        logger.info("Token refresh successful")
        return access_token

    def logout_user(self, refresh_token: str) -> None:
        """Revoke the given refresh token and its associated access token.

        Uses Cognito's RevokeToken API, which invalidates the specific token
        family without affecting other active sessions for the same user.

        Args:
            refresh_token: The Cognito refresh token issued at sign-in.

        Raises:
            ApplicationException: 401 if the token is invalid or already expired;
                500 for unexpected Cognito errors.

        """
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
                raise ApplicationException(
                    code=401, content="Invalid or expired token"
                ) from exc
            logger.error("revoke_token failed", error_code=error_code, error=str(exc))
            raise ApplicationException(code=500, content="Logout failed") from exc

    def get_identity_from_access_token(self, access_token: str) -> tuple[str, UserRole]:
        """Validate the access token and return (user_id, role) extracted from claims."""
        try:
            self._client.get_user(AccessToken=access_token)
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in (
                "NotAuthorizedException",
                "InvalidParameterException",
                "ResourceNotFoundException",
            ):
                raise ApplicationException(
                    code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                    content="Invalid or expired access token",
                ) from exc
            logger.error("get_user failed", error_code=error_code, error=str(exc))
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_INTERNAL_SERVER_ERROR,
                content="Failed to validate access token",
            ) from exc

        claims = decode_access_token_payload(access_token)
        if claims.get("token_use") != "access":
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                content="Invalid or expired access token",
            )

        sub = claims.get("sub")
        if not isinstance(sub, str):
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                content="Invalid or expired access token",
            )

        try:
            UUID(sub)
        except ValueError as exc:
            raise ApplicationException(
                code=HttpStatusCode.RESPONSE_UNAUTHORIZED,
                content="Invalid or expired access token",
            ) from exc

        groups = claims.get("cognito:groups", [])
        if not isinstance(groups, list):
            groups = [groups] if isinstance(groups, str) else []

        for role in UserRole:
            if role.value in groups:
                return sub, role

        raise ApplicationException(
            code=HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
            content="Role is not supported for this endpoint",
        )

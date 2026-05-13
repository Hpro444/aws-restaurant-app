"""Service layer for AWS Cognito user management."""

import boto3
from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import get_logger
from domain.auth_result import AuthResult
from enums.user_role import UserRole
from pydantic import SecretStr

_LOG = get_logger(__name__)


class CognitoService:
    """Wraps boto3 Cognito IdP calls for user registration and authentication."""

    def __init__(self) -> None:
        """Initialise settings, boto3 Cognito client, pool ID cache, and JWT service."""
        self._settings = AppConfig()
        self._client = boto3.client(
            "cognito-idp", region_name=self._settings.aws_region
        )
        self._pool_id: str | None = None
        self._client_id: str | None = None

    def _resolve_pool_id(self) -> str:
        """Return the Cognito User Pool ID, resolving it by name on first call.

        Paginates list_user_pools until a pool whose Name contains the value
        of the USER_POOL_NAME environment variable is found, then caches the
        result for the lifetime of the Lambda execution context.

        Raises:
            ApplicationException: 500 if the pool cannot be found.

        """
        if self._pool_id:
            _LOG.debug("Pool ID cache hit: %s", self._pool_id)
            return self._pool_id

        pool_name = self._settings.user_pool_name
        _LOG.info("Resolving pool ID for name containing '%s'", pool_name)
        paginator_token = None

        while True:
            kwargs = {"MaxResults": self._settings.cognito_max_results}
            if paginator_token:
                kwargs["NextToken"] = paginator_token

            response = self._client.list_user_pools(**kwargs)

            for pool in response.get("UserPools", []):
                if pool_name in pool["Name"]:
                    self._pool_id = pool["Id"]
                    _LOG.info("Resolved pool '%s' -> %s", pool["Name"], self._pool_id)
                    self._ensure_groups(self._pool_id)
                    return self._pool_id

            paginator_token = response.get("NextToken")
            if not paginator_token:
                break

        _LOG.error("No user pool found containing '%s'", pool_name)
        raise ApplicationException(
            code=500, content=f"Cognito user pool containing '{pool_name}' not found"
        )

    _GROUP_DEFINITIONS: tuple[tuple[str, str, int], ...] = (
        ("Admin", "Administrators group", 1),
        ("Waiter", "Waiters group", 5),
        ("User", "Regular users group", 10),
    )

    def _ensure_groups(self, pool_id: str) -> None:
        """Create any missing Cognito user pool groups defined in _GROUP_DEFINITIONS.

        Idempotent — existing groups are left untouched.
        """
        _LOG.info("Ensuring groups exist for pool %s", pool_id)
        try:
            existing = {
                g["GroupName"]
                for g in self._client.list_groups(UserPoolId=pool_id).get("Groups", [])
            }
        except ClientError as exc:
            _LOG.error("list_groups failed: %s", exc)
            return

        _LOG.debug("Existing groups: %s", existing)
        for name, description, precedence in self._GROUP_DEFINITIONS:
            if name in existing:
                _LOG.debug("Group '%s' already exists, skipping", name)
                continue
            try:
                self._client.create_group(
                    UserPoolId=pool_id,
                    GroupName=name,
                    Description=description,
                    Precedence=precedence,
                )
                _LOG.info("Created Cognito group '%s'", name)
            except ClientError as exc:
                _LOG.error("create_group '%s' failed: %s", name, exc)

    def _resolve_client_id(self, pool_id: str) -> str:
        """Return the app client ID for the given pool, resolving it on first call.

        Raises:
            ApplicationException: 500 if no client is found for the pool.

        """
        if self._client_id:
            _LOG.debug("Client ID cache hit: %s", self._client_id)
            return self._client_id

        _LOG.info("Resolving app client ID for pool %s", pool_id)
        try:
            response = self._client.list_user_pool_clients(
                UserPoolId=pool_id, MaxResults=10
            )
        except ClientError as exc:
            _LOG.error("list_user_pool_clients failed: %s", exc)
            raise ApplicationException(
                code=500, content="Failed to resolve Cognito app client"
            ) from exc

        clients = response.get("UserPoolClients", [])
        if not clients:
            _LOG.error("No app clients found for pool %s", pool_id)
            raise ApplicationException(
                code=500, content="No Cognito app client found for pool"
            )
        self._client_id = clients[0]["ClientId"]
        _LOG.info(
            "Resolved client '%s' -> %s", clients[0].get("ClientName"), self._client_id
        )
        return self._client_id

    def register_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password: SecretStr,
        role: UserRole = UserRole.USER,
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
            role: Role to assign via group membership; defaults to UserRole.USER.

        Returns:
            The Cognito `sub` UUID for the newly created user.

        Raises:
            ApplicationException: 409 if the email is already registered,
                500 for any other Cognito error.

        """
        _LOG.info("Registering user email=%s role=%s", email, role.value)
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
                _LOG.warning("Registration rejected — email already exists: %s", email)
                raise ApplicationException(
                    code=409, content="Registration failed"
                ) from exc
            _LOG.error("admin_create_user failed [%s]: %s", code, exc)
            raise ApplicationException(
                code=500, content="Failed to create user"
            ) from exc

        user_id = next(
            attr["Value"]
            for attr in response["User"]["Attributes"]
            if attr["Name"] == "sub"
        )
        _LOG.info(
            "User created sub=%s status=%s", user_id, response["User"]["UserStatus"]
        )

        try:
            self._client.admin_set_user_password(
                UserPoolId=pool_id,
                Username=email,
                Password=password.get_secret_value(),
                Permanent=True,
            )
            _LOG.info("Password set permanently for %s", email)
        except ClientError as exc:
            _LOG.error(
                "admin_set_user_password failed [%s]: %s",
                exc.response["Error"]["Code"],
                exc,
            )
            raise ApplicationException(
                code=500, content="Failed to confirm user account"
            ) from exc

        try:
            self._client.admin_add_user_to_group(
                UserPoolId=pool_id, Username=email, GroupName=role.value
            )
            _LOG.info("Assigned user %s to group '%s'", email, role.value)
        except ClientError as exc:
            _LOG.error(
                "admin_add_user_to_group failed [%s]: %s",
                exc.response["Error"]["Code"],
                exc,
            )
            raise ApplicationException(
                code=500, content="Failed to assign user role"
            ) from exc

        return user_id

    def authenticate_user(self, email: str, password: SecretStr) -> AuthResult:
        """Authenticate a user via Cognito and return the issued access token.

        Delegates credential verification entirely to Cognito using the
        ADMIN_USER_PASSWORD_AUTH flow. Both "user not found" and "wrong password"
        surface as NotAuthorizedException, which is mapped to 401 to prevent
        user enumeration.

        Args:
            email: Normalised user email (already lowercased/trimmed by the DTO).
            password: Plaintext password provided by the caller.

        Returns:
            AuthResult with Cognito's AccessToken, the user's full name, and role.

        Raises:
            ApplicationException: 401 for invalid credentials; 500 for unexpected
                Cognito errors.

        """
        _LOG.info("Authenticating user email=%s", email)
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
                _LOG.warning("initiate_auth rejected [%s]: %s", error_code, exc)
                raise ApplicationException(
                    code=401, content="Invalid credentials"
                ) from exc
            _LOG.error("initiate_auth failed [%s]: %s", error_code, exc)
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

        access_token = auth_response["AuthenticationResult"]["AccessToken"]
        refresh_token = auth_response["AuthenticationResult"]["RefreshToken"]
        _LOG.info("Cognito auth successful for %s", email)

        try:
            user_response = self._client.admin_get_user(
                UserPoolId=pool_id, Username=email
            )
        except ClientError as exc:
            _LOG.error(
                "admin_get_user failed [%s]: %s", exc.response["Error"]["Code"], exc
            )
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

        attrs = {
            attr["Name"]: attr["Value"] for attr in user_response["UserAttributes"]
        }
        first_name = attrs.get("custom:first_name", "")
        last_name = attrs.get("custom:last_name", "")
        _LOG.debug(
            "Fetched user attributes for %s: first_name=%s last_name=%s",
            email,
            first_name,
            last_name,
        )

        try:
            groups_response = self._client.admin_list_groups_for_user(
                UserPoolId=pool_id, Username=email
            )
        except ClientError as exc:
            _LOG.error(
                "admin_list_groups_for_user failed [%s]: %s",
                exc.response["Error"]["Code"],
                exc,
            )
            raise ApplicationException(
                code=500, content="Authentication failed"
            ) from exc

        groups = groups_response.get("Groups", [])
        role = groups[0]["GroupName"] if groups else ""
        _LOG.info("User %s authenticated with role='%s'", email, role)

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
        _LOG.info("Refreshing tokens")
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
                _LOG.warning("Token refresh rejected [%s]: %s", error_code, exc)
                raise ApplicationException(
                    code=401, content="Invalid or expired refresh token"
                ) from exc
            _LOG.error("Token refresh failed [%s]: %s", error_code, exc)
            raise ApplicationException(
                code=500, content="Token refresh failed"
            ) from exc

        access_token = response["AuthenticationResult"]["AccessToken"]
        _LOG.info("Token refresh successful")
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
        _LOG.info("Revoking refresh token")
        pool_id = self._resolve_pool_id()
        client_id = self._resolve_client_id(pool_id)

        try:
            self._client.revoke_token(Token=refresh_token, ClientId=client_id)
            _LOG.info("Token revoked successfully")
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in ("NotAuthorizedException", "TokenExpiredException"):
                _LOG.warning("Token revocation rejected [%s]: %s", error_code, exc)
                raise ApplicationException(
                    code=401, content="Invalid or expired token"
                ) from exc
            _LOG.error("revoke_token failed [%s]: %s", error_code, exc)
            raise ApplicationException(code=500, content="Logout failed") from exc

"""Service layer for AWS Cognito user management."""

import os

import boto3
from argon2 import PasswordHasher
from botocore.exceptions import ClientError
from commons.exceptions import ApplicationException
from commons.log_helper import get_logger
from enums.user_role import UserRole

_LOG = get_logger(__name__)
_PH = PasswordHasher()


class CognitoService:
    """Wraps boto3 Cognito IdP calls for user registration."""

    _USER_POOL_NAME_ENV = "USER_POOL_NAME"
    _MAX_RESULTS = 60

    _DEFAULT_REGION = "eu-west-3"

    def __init__(self):
        """Initialise the boto3 Cognito client and prepare pool ID cache."""
        region = os.environ.get("AWS_REGION", self._DEFAULT_REGION)
        self._client = boto3.client("cognito-idp", region_name=region)
        self._pool_id: str | None = None

    def _resolve_pool_id(self) -> str:
        """Return the Cognito User Pool ID, resolving it by name on first call.

        Paginates list_user_pools until a pool whose Name contains the value
        of the USER_POOL_NAME environment variable is found, then caches the
        result for the lifetime of the Lambda execution context.

        Raises:
            ApplicationException: 500 if the pool cannot be found.
        """
        if self._pool_id:
            return self._pool_id

        pool_name = os.environ.get(self._USER_POOL_NAME_ENV, "")
        paginator_token = None

        while True:
            kwargs = {"MaxResults": self._MAX_RESULTS}
            if paginator_token:
                kwargs["NextToken"] = paginator_token

            response = self._client.list_user_pools(**kwargs)

            for pool in response.get("UserPools", []):
                if pool_name in pool["Name"]:
                    self._pool_id = pool["Id"]
                    return self._pool_id

            paginator_token = response.get("NextToken")
            if not paginator_token:
                break

        raise ApplicationException(code=500, content=f"Cognito user pool containing '{pool_name}' not found")

    def register_user(self, first_name: str, last_name: str, email: str, password: str, role: UserRole = UserRole.USER) -> str:
        """Create a confirmed user in Cognito and return their sub (userId).

        Hashes the password with Argon2id and stores the hash as a custom
        attribute. The plaintext password is never logged.

        Args:
            first_name: User's given name.
            last_name: User's family name.
            email: User's email address, used as the Cognito username.
            password: Plaintext password; hashed with Argon2id before storage.
            role: Role to assign; defaults to UserRole.USER.

        Returns:
            The Cognito `sub` UUID for the newly created user.

        Raises:
            ApplicationException: 409 if the email is already registered,
                500 for any other Cognito error.
        """
        pool_id = self._resolve_pool_id()
        password_hash = _PH.hash(password)

        try:
            response = self._client.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:first_name", "Value": first_name},
                    {"Name": "custom:last_name", "Value": last_name},
                    {"Name": "custom:role", "Value": role.value},
                    {"Name": "custom:password", "Value": password_hash},
                ],
                MessageAction="SUPPRESS",
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "UsernameExistsException":
                raise ApplicationException(code=409, content="Registration failed") from exc
            _LOG.error("admin_create_user failed: %s", exc)
            raise ApplicationException(code=500, content="Failed to create user") from exc

        user_id = next(attr["Value"] for attr in response["User"]["Attributes"] if attr["Name"] == "sub")

        try:
            self._client.admin_set_user_password(UserPoolId=pool_id, Username=email, Password=password, Permanent=True)
        except ClientError as exc:
            _LOG.error("admin_set_user_password failed: %s", exc)
            raise ApplicationException(code=500, content="Failed to confirm user account") from exc

        return user_id

"""Seed module: create demo Cognito users for all customers and waiters.

Creates (or verifies) each user account in Cognito, sets a fixed demo password,
and assigns them to the appropriate group. Stores the Cognito sub for every user
in ``context["cognito_subs"]`` so that downstream seeders (customers, waiters)
can use the Cognito sub as the DynamoDB primary key.

This module is idempotent: re-running it when users already exist silently
retrieves their existing subs and resets the password.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

_POOL_NAME_BASE = "restaurant-userpool"
_DEMO_PASSWORD = "Password123@"
_MAX_POOL_RESULTS = 60

_GROUP_DEFINITIONS = [
    ("Admin", "Administrators group", 1),
    ("Waiter", "Waiters group", 5),
    ("Customer", "Regular users group", 10),
]

# (email, first_name, last_name, cognito_group)
_USERS: list[tuple[str, str, str, str]] = [
    ("alice@example.com", "Alice", "Smith", "Customer"),
    ("bob@example.com", "Bob", "Johnson", "Customer"),
    ("carol@example.com", "Carol", "Williams", "Customer"),
    ("david@example.com", "David", "Brown", "Customer"),
    ("emma@example.com", "Emma", "Davis", "Customer"),
    ("frank@example.com", "Frank", "Miller", "Customer"),
    ("grace@example.com", "Grace", "Wilson", "Customer"),
    ("henry@example.com", "Henry", "Moore", "Customer"),
    ("iris@example.com", "Iris", "Taylor", "Customer"),
    ("james@example.com", "James", "Anderson", "Customer"),
    ("kate@example.com", "Kate", "Thompson", "Customer"),
    ("lea@example.com", "Lea", "Martinez", "Waiter"),
    ("charlie@example.com", "Charlie", "Petrov", "Waiter"),
    ("olivia@example.com", "Olivia", "Mchedlishvili", "Waiter"),
    ("ethan@example.com", "Ethan", "Kapanadze", "Waiter"),
    ("max@example.com", "Max", "Fischer", "Waiter"),
    ("sofia@example.com", "Sofia", "Abashidze", "Waiter"),
    ("liam@example.com", "Liam", "Gelashvili", "Waiter"),
    ("mia@example.com", "Mia", "Gogoladze", "Waiter"),
    ("nina@example.com", "Nina", "Beridze", "Waiter"),
    ("noah@example.com", "Noah", "Chelidze", "Waiter"),
    ("ava@example.com", "Ava", "Dolidze", "Waiter"),
    ("luka@example.com", "Luka", "Maisuradze", "Waiter"),
]


def _resolve_pool_id(cognito_client, pool_name: str) -> str:
    """Return the User Pool ID whose name matches ``pool_name`` exactly, or contains it as a fallback.

    Args:
        cognito_client: Boto3 Cognito IDP client.
        pool_name: Full expected pool name (e.g. ``tm3-restaurant-userpool-dev4``).

    Raises:
        RuntimeError: If no matching pool is found.

    """
    next_token = None
    while True:
        params: dict = {"MaxResults": _MAX_POOL_RESULTS}
        if next_token:
            params["NextToken"] = next_token
        response = cognito_client.list_user_pools(**params)
        for pool in response.get("UserPools", []):
            if pool["Name"] == pool_name or pool_name in pool["Name"]:
                return pool["Id"]
        next_token = response.get("NextToken")
        if not next_token:
            break
    raise RuntimeError(f"No Cognito user pool found matching '{pool_name}'")


def _ensure_groups(cognito_client, pool_id: str) -> None:
    """Create any missing Cognito groups defined in ``_GROUP_DEFINITIONS``."""
    try:
        existing = {
            g["GroupName"]
            for g in cognito_client.list_groups(UserPoolId=pool_id).get("Groups", [])
        }
    except ClientError as exc:
        print(f"  ⚠ Could not list Cognito groups: {exc}")
        return
    for name, description, precedence in _GROUP_DEFINITIONS:
        if name in existing:
            continue
        try:
            cognito_client.create_group(
                UserPoolId=pool_id,
                GroupName=name,
                Description=description,
                Precedence=precedence,
            )
        except ClientError as exc:
            print(f"  ⚠ Could not create group '{name}': {exc}")


def _get_or_create_user(
    cognito_client,
    pool_id: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """Create a Cognito user (or fetch existing) and return their sub UUID string."""
    try:
        response = cognito_client.admin_create_user(
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
        return next(
            attr["Value"]
            for attr in response["User"]["Attributes"]
            if attr["Name"] == "sub"
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "UsernameExistsException":
            raise
    # User already exists — fetch their sub.
    response = cognito_client.admin_get_user(UserPoolId=pool_id, Username=email)
    return next(
        attr["Value"] for attr in response["UserAttributes"] if attr["Name"] == "sub"
    )


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Create demo Cognito users and store their subs in ``context["cognito_subs"]``.

    Args:
        dynamodb: Unused; present for interface consistency.
        tables: Unused; present for interface consistency.
        context: Seed context dict; must contain ``aws_credentials`` (may be empty)
            and ``aws_region``. Populates ``context["cognito_subs"]``.

    """
    creds = context.get("aws_credentials", {})
    region = context.get("aws_region", "eu-west-3")
    prefix = context.get("resources_prefix", "")
    suffix = context.get("resources_suffix", "")
    cognito_client = boto3.client("cognito-idp", region_name=region, **creds)

    pool_name = f"{prefix}{_POOL_NAME_BASE}{suffix}"
    pool_id = _resolve_pool_id(cognito_client, pool_name)
    _ensure_groups(cognito_client, pool_id)

    subs: dict[str, str] = {}
    created = 0
    existing = 0

    for email, first_name, last_name, group in _USERS:
        try:
            cognito_client.admin_get_user(UserPoolId=pool_id, Username=email)
            user_existed = True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "UserNotFoundException":
                user_existed = False
            else:
                raise

        sub = _get_or_create_user(cognito_client, pool_id, email, first_name, last_name)

        cognito_client.admin_set_user_password(
            UserPoolId=pool_id,
            Username=email,
            Password=_DEMO_PASSWORD,
            Permanent=True,
        )
        cognito_client.admin_add_user_to_group(
            UserPoolId=pool_id,
            Username=email,
            GroupName=group,
        )

        subs[email] = sub
        if user_existed:
            existing += 1
        else:
            created += 1

    context["cognito_subs"] = subs
    print(
        f"  ✓ Cognito users: {created} created, {existing} already existed "
        f"(password set to '{_DEMO_PASSWORD}' for all)"
    )

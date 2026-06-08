#!/usr/bin/env python3
"""Generate or refresh Cognito access tokens for seeded demo users.

Tokens are written to tokens.json (gitignored) so any test script can read
them without re-authenticating. The file is keyed by email and stores the
access token, refresh token, and Cognito group for each user.

Usage:
    python generate_tokens.py                             # auth all seeded users
    python generate_tokens.py --refresh                   # refresh all tokens
    python generate_tokens.py --email alice@example.com   # auth one user
    python generate_tokens.py --email alice@example.com --refresh
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

sys.path.insert(0, str(Path(__file__).parent))

from seeds.cognito_users import (
    _DEMO_PASSWORD,
    _POOL_NAME_BASE,
    _USERS,
    _resolve_pool_id,
)
from seeds.config import AWS_REGION

TOKENS_FILE = Path(__file__).parent / "tokens.json"

_SYNDICATE_CONFIG = (
    Path(__file__).parent
    / "restaurant-backend-app"
    / ".syndicate-config-dev"
    / "syndicate.yml"
)


def _extract_config_value(content: str, key: str) -> str | None:
    """Extract a plain scalar value from a simple YAML ``key: value`` line."""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", content, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return value or None


def _load_syndicate_credentials() -> dict:
    """Return AWS credential kwargs from syndicate.yml, or empty dict to fall back to env/profile."""
    if not _SYNDICATE_CONFIG.exists():
        return {}
    content = _SYNDICATE_CONFIG.read_text(encoding="utf-8")
    access_key = _extract_config_value(content, "temp_aws_access_key_id")
    secret_key = _extract_config_value(content, "temp_aws_secret_access_key")
    session_token = _extract_config_value(content, "temp_aws_session_token")
    if not (access_key and secret_key and session_token):
        access_key = _extract_config_value(content, "aws_access_key_id")
        secret_key = _extract_config_value(content, "aws_secret_access_key")
        session_token = _extract_config_value(content, "aws_session_token")
    if access_key and secret_key and session_token:
        return {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "aws_session_token": session_token,
        }
    return {}


def _load_tokens() -> dict:
    """Load existing token entries from tokens.json, or return an empty dict."""
    if TOKENS_FILE.exists():
        return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_tokens(tokens: dict) -> None:
    """Persist token entries to tokens.json."""
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _resolve_client_id(cognito_client, pool_id: str) -> str:
    """Return the first app client ID registered for the given Cognito pool.

    Raises:
        RuntimeError: If no app clients are found.

    """
    response = cognito_client.list_user_pool_clients(UserPoolId=pool_id, MaxResults=10)
    clients = response.get("UserPoolClients", [])
    if not clients:
        raise RuntimeError(f"No app clients found for pool '{pool_id}'")
    return clients[0]["ClientId"]


def _authenticate(cognito_client, client_id: str, email: str) -> dict:
    """Authenticate with the demo password and return access + refresh tokens.

    Args:
        cognito_client: Boto3 Cognito IDP client.
        client_id: Cognito app client ID.
        email: User email (also used as Cognito username).

    Returns:
        Dict with ``access_token`` and ``refresh_token`` keys.

    """
    response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": _DEMO_PASSWORD},
    )
    result = response["AuthenticationResult"]
    return {
        "access_token": result["AccessToken"],
        "refresh_token": result["RefreshToken"],
    }


def _do_refresh(cognito_client, client_id: str, refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token.

    The Cognito refresh flow does not issue a new refresh token, so the
    caller must preserve the original one.

    Args:
        cognito_client: Boto3 Cognito IDP client.
        client_id: Cognito app client ID.
        refresh_token: Stored refresh token for the user.

    Returns:
        Dict with only the ``access_token`` key updated.

    """
    response = cognito_client.initiate_auth(
        ClientId=client_id,
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={"REFRESH_TOKEN": refresh_token},
    )
    return {"access_token": response["AuthenticationResult"]["AccessToken"]}


def generate_all(context: dict | None = None) -> None:
    """Authenticate every seeded user and write their tokens to tokens.json.

    Designed to be called from quick_seed.py immediately after seeding
    completes. Accepts the seed context dict so it can reuse already-loaded
    AWS credentials and resource prefix/suffix values.

    Args:
        context: Seed context dict; may contain ``aws_credentials``,
            ``aws_region``, ``resources_prefix``, ``resources_suffix``.
            Falls back to syndicate config / env when absent.

    """
    if context is None:
        context = {}

    creds = context.get("aws_credentials") or _load_syndicate_credentials()
    region = context.get("aws_region", AWS_REGION)

    # prefix/suffix select the exact pool (e.g. tm3-restaurant-userpool-dev1).
    # When called without a seed context, derive them from syndicate.yml — an
    # empty prefix/suffix yields the bare "restaurant-userpool", which matches
    # every env's pool by substring and would resolve to the wrong one.
    syndicate_content = (
        _SYNDICATE_CONFIG.read_text(encoding="utf-8")
        if _SYNDICATE_CONFIG.exists()
        else ""
    )
    prefix = (
        context.get("resources_prefix")
        or _extract_config_value(syndicate_content, "resources_prefix")
        or ""
    )
    suffix = (
        context.get("resources_suffix")
        or _extract_config_value(syndicate_content, "resources_suffix")
        or ""
    )

    cognito_client = boto3.client("cognito-idp", region_name=region, **creds)
    pool_name = f"{prefix}{_POOL_NAME_BASE}{suffix}"
    try:
        pool_id = _resolve_pool_id(cognito_client, pool_name)
        client_id = _resolve_client_id(cognito_client, pool_id)
    except (RuntimeError, ClientError) as exc:
        raise RuntimeError(
            f"Cannot generate tokens for syndicate pool '{pool_name}': {exc}"
        ) from exc

    tokens: dict = {}
    ok = 0
    failed = 0

    for email, _, _, group in _USERS:
        try:
            tok = _authenticate(cognito_client, client_id, email)
            tokens[email] = {"group": group, **tok}
            ok += 1
        except ClientError as exc:
            print(f"  ⚠ {email}: {exc.response['Error']['Message']}")
            failed += 1

    _save_tokens(tokens)
    status = f"{ok} ok" + (f", {failed} failed" if failed else "")
    print(f"  ✓ tokens.json written ({status})")


def main() -> int:
    """CLI entrypoint — parse args and generate or refresh tokens."""
    parser = argparse.ArgumentParser(
        description="Generate or refresh Cognito tokens for seeded demo users.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python generate_tokens.py\n"
            "  python generate_tokens.py --refresh\n"
            "  python generate_tokens.py --email alice@example.com\n"
            "  python generate_tokens.py --email alice@example.com --refresh\n"
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Use stored refresh tokens instead of re-authenticating with the password.",
    )
    parser.add_argument(
        "--email",
        metavar="EMAIL",
        help="Target a single user by email. Defaults to all seeded users.",
    )
    args = parser.parse_args()

    creds = _load_syndicate_credentials()
    if not creds:
        print("▶ Using AWS credentials from environment / profile")

    try:
        session = boto3.session.Session(region_name=AWS_REGION, **creds)
        cognito_client = session.client("cognito-idp", region_name=AWS_REGION)
    except (ClientError, NoCredentialsError) as exc:
        print(f"✗ Could not create Cognito client: {exc}")
        return 1

    syndicate_content = (
        _SYNDICATE_CONFIG.read_text(encoding="utf-8")
        if _SYNDICATE_CONFIG.exists()
        else ""
    )
    prefix = _extract_config_value(syndicate_content, "resources_prefix") or ""
    suffix = _extract_config_value(syndicate_content, "resources_suffix") or ""
    pool_name = f"{prefix}{_POOL_NAME_BASE}{suffix}"

    try:
        pool_id = _resolve_pool_id(cognito_client, pool_name)
        client_id = _resolve_client_id(cognito_client, pool_id)
    except (RuntimeError, ClientError) as exc:
        print(f"✗ Cannot generate tokens for syndicate pool '{pool_name}': {exc}")
        return 1

    all_seeded = {email: group for email, _, _, group in _USERS}

    if args.email:
        if args.email not in all_seeded:
            valid = ", ".join(all_seeded)
            print(f"✗ '{args.email}' is not a seeded user.\n  Valid emails: {valid}")
            return 1
        target = {args.email: all_seeded[args.email]}
    else:
        target = all_seeded

    tokens = _load_tokens()
    ok = 0
    failed = 0

    print(
        f"▶ {'Refreshing' if args.refresh else 'Authenticating'} {len(target)} user(s)..."
    )

    for email, group in target.items():
        try:
            if args.refresh:
                stored = tokens.get(email, {})
                rt = stored.get("refresh_token")
                if not rt:
                    print(
                        f"  ⚠ No stored refresh token for {email} — falling back to password auth"
                    )
                    tok = _authenticate(cognito_client, client_id, email)
                else:
                    partial = _do_refresh(cognito_client, client_id, rt)
                    tok = {**stored, **partial}
            else:
                tok = _authenticate(cognito_client, client_id, email)

            tokens[email] = {"group": group, **tok}
            print(f"  ✓ {email} ({group})")
            ok += 1
        except ClientError as exc:
            print(f"  ✗ {email}: {exc.response['Error']['Message']}")
            failed += 1

    _save_tokens(tokens)
    status = f"{ok} ok" + (f", {failed} failed" if failed else "")
    print(f"\n✓ tokens.json updated ({status})")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

"""Shared execution context passed to every e2e suite module."""

from __future__ import annotations

from e2e.recorder import Recorder


class E2EContext:
    """Carries tokens, seeded IDs, AWS handles, and cross-suite state.

    Suites communicate through ``state`` — e.g. the bookings suite stores the
    created reservation id, which the orders and feedbacks suites reuse —
    the same way seed modules pass data through their ``context`` dict.
    """

    def __init__(
        self,
        base_url: str,
        tokens: dict[str, str],
        ids: dict,
        dynamodb,
        tables: dict[str, object],
    ) -> None:
        """Store connection handles and initialize the shared state dict.

        Args:
            base_url: Resolved API Gateway invoke URL including the stage.
            tokens: Access tokens keyed by user email (from tokens.json).
            ids: Seeded entity IDs (from ids.json).
            dynamodb: boto3 DynamoDB service resource.
            tables: boto3 Table objects keyed by logical alias.

        """
        self.base_url = base_url.rstrip("/")
        self.tokens = tokens
        self.ids = ids
        self.dynamodb = dynamodb
        self.tables = tables
        self.recorder = Recorder()
        self.state: dict = {}

    def token(self, email: str) -> str:
        """Return the cached access token for a seeded user email."""
        return self.tokens.get(email, "")

    def table(self, alias: str):
        """Return the boto3 Table for a logical alias, or None when missing."""
        return self.tables.get(alias)

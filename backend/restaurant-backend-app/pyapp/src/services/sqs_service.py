"""Generic SQS publisher for sending Pydantic model payloads."""

from __future__ import annotations

import boto3
from commons.app_config import AppConfig
from commons.log_helper import logger
from pydantic import BaseModel


class SqsService:
    """Publishes any Pydantic model as a JSON message to Amazon SQS.

    Publishing is best-effort: all exceptions are caught and logged so that
    SQS failures never interrupt the HTTP response path. The service is
    payload-agnostic — callers construct the specific event envelope (e.g.
    ``ReservationEventMessage``) and pass it to :meth:`publish`.
    """

    def __init__(
        self,
        settings: AppConfig | None = None,
        client: object | None = None,
    ) -> None:
        """Initialise settings and defer SQS client creation until first use.

        Args:
            settings: Application config; a fresh instance is created when omitted.
            client: Optional pre-built boto3 SQS client injected in tests.

        """
        self._settings = settings or AppConfig()
        self._client = client

    def _get_client(self) -> object:
        """Return the boto3 SQS client, creating it lazily on first call."""
        if self._client is None:
            self._client = boto3.client("sqs", region_name=self._settings.aws_region)
        return self._client

    def publish(self, queue_url: str, message: BaseModel) -> None:
        """Publish ``message`` to ``queue_url`` as a JSON string.

        If ``queue_url`` is empty (local dev or unit tests without SQS) the call
        is silently skipped. Any exception from boto3 or serialisation is caught,
        logged at ERROR level, and swallowed so SQS failures never interrupt the
        HTTP response path.

        Args:
            queue_url: Full SQS queue URL. Empty string skips publishing.
            message: Any Pydantic ``BaseModel``; serialised with ``by_alias=True``
                so camelCase field aliases are used in the JSON output.

        """
        if not queue_url:
            logger.debug("SQS publish skipped — queue URL not configured")
            return
        try:
            body = message.model_dump_json(by_alias=True)
            self._get_client().send_message(QueueUrl=queue_url, MessageBody=body)
            logger.info("SQS message published", queue_url=queue_url)
        except Exception:
            logger.error(
                "Failed to publish SQS message — continuing",
                queue_url=queue_url,
                exc_info=True,
            )

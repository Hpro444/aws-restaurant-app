"""Abstract DynamoDB CRUD repository shared by all domain repositories."""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from commons.app_config import AppConfig
from commons.dynamo_model import DynamoModel
from commons.exceptions import ApplicationException
from commons.log_helper import logger

T = TypeVar("T", bound=DynamoModel)


class DynamoRepository(ABC, Generic[T]):
    """Abstract CRUD repository for a single DynamoDB table.

    Subclasses pass the table alias and model class to the constructor.
    The table name is resolved at runtime by scanning DynamoDB table names
    for one whose name contains the alias, then cached for the Lambda
    container lifetime — the same pattern used by LoginAttemptsService.
    """

    _pk_field: ClassVar[str] = "id"

    def __init__(
        self,
        table_alias: str,
        model_class: type[T],
        settings: AppConfig | None = None,
    ) -> None:
        """Initialise the DynamoDB client, table alias, and model class.

        Args:
            table_alias: Substring used to resolve the full DynamoDB table name.
            model_class: The DynamoModel subclass to deserialize items into.
            settings: Application config; a fresh instance is created when omitted.

        """
        cfg = settings or AppConfig()
        self._table_alias = table_alias
        self._model_class = model_class
        self._resolved_table_name: str | None = None
        self._client = boto3.client("dynamodb", region_name=cfg.aws_region)

    def _resolve_table_name(self) -> str:
        """Return the actual DynamoDB table name, resolving it by alias on first call.

        Paginates list_tables until a table whose name contains _table_alias is
        found, then caches the result for the lifetime of the Lambda context.
        Falls back to the raw alias when no matching table is found.

        Returns:
            The fully-qualified table name as deployed.

        """
        if self._resolved_table_name:
            return self._resolved_table_name

        logger.info("Resolving DynamoDB table name", alias=self._table_alias)
        last_evaluated = None

        while True:
            params: dict[str, Any] = {"Limit": 100}
            if last_evaluated:
                params["ExclusiveStartTableName"] = last_evaluated

            try:
                response = self._client.list_tables(**params)
            except ClientError as exc:
                logger.error("list_tables failed", error=str(exc))
                break

            for name in response.get("TableNames", []):
                if self._table_alias in name:
                    self._resolved_table_name = name
                    logger.info(
                        "Resolved table name", alias=self._table_alias, table=name
                    )
                    return name

            last_evaluated = response.get("LastEvaluatedTableName")
            if not last_evaluated:
                break

        logger.info("No table found, falling back to alias", alias=self._table_alias)
        self._resolved_table_name = self._table_alias
        return self._table_alias

    def create(self, item: T) -> None:
        """Persist a new item; raises ApplicationException(409) if the id already exists.

        Args:
            item: The domain model instance to persist.

        """
        try:
            self._client.put_item(
                TableName=self._resolve_table_name(),
                Item=item.to_dynamodb_item(),
                ConditionExpression=f"attribute_not_exists({self._pk_field})",
            )
            logger.info("Item created", table=self._table_alias, id=str(item.id))
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApplicationException(
                    409, f"Item with id '{item.id}' already exists."
                )
            logger.error("DynamoDB put_item (create) failed", error=str(exc))

    def get(self, item_id: UUID) -> T | None:
        """Return the item with the given id, or None if it does not exist.

        Args:
            item_id: The UUID primary key of the item to retrieve.

        """
        try:
            response = self._client.get_item(
                TableName=self._resolve_table_name(),
                Key={self._pk_field: {"S": str(item_id)}},
            )
        except ClientError as exc:
            logger.error("DynamoDB get_item failed", id=str(item_id), error=str(exc))
            return None

        raw = response.get("Item")
        if not raw:
            return None
        return self._model_class.from_dynamodb_item(raw)

    def update(self, item: T) -> None:
        """Replace the stored item with the given model (full document replace).

        Args:
            item: The domain model instance carrying the updated state.

        """
        try:
            self._client.put_item(
                TableName=self._resolve_table_name(),
                Item=item.to_dynamodb_item(),
            )
            logger.info("Item updated", table=self._table_alias, id=str(item.id))
        except ClientError as exc:
            logger.error("DynamoDB put_item (update) failed", error=str(exc))

    def delete(self, item_id: UUID) -> None:
        """Delete the item with the given id.

        Args:
            item_id: The UUID primary key of the item to delete.

        """
        try:
            self._client.delete_item(
                TableName=self._resolve_table_name(),
                Key={self._pk_field: {"S": str(item_id)}},
            )
            logger.info("Item deleted", table=self._table_alias, id=str(item_id))
        except ClientError as exc:
            logger.error("DynamoDB delete_item failed", id=str(item_id), error=str(exc))

    def scan(self) -> list[T]:
        """Return all items in the table, paginating automatically.

        Returns:
            A list of deserialized domain model instances.

        """
        table = self._resolve_table_name()
        items: list[T] = []
        params: dict[str, Any] = {"TableName": table}

        while True:
            try:
                response = self._client.scan(**params)
            except ClientError as exc:
                logger.error(
                    "DynamoDB scan failed", table=self._table_alias, error=str(exc)
                )
                return items

            items.extend(
                self._model_class.from_dynamodb_item(raw)
                for raw in response.get("Items", [])
            )

            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            params["ExclusiveStartKey"] = last_key

        return items

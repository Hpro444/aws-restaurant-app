"""DynamoDB snapshot and polling helpers used by the e2e suites."""

from __future__ import annotations

import time
from decimal import Decimal

from boto3.dynamodb.conditions import Attr

from e2e.recorder import DbCheck


def dec_to_native(value):
    """Recursively convert DynamoDB Decimal values to int/float."""
    if isinstance(value, dict):
        return {k: dec_to_native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [dec_to_native(v) for v in value]
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    return value


def get_by_id(table, item_id) -> dict | None:
    """Fetch one row by its ``id`` primary key, or None when absent."""
    if table is None:
        return None
    resp = table.get_item(Key={"id": str(item_id)})
    item = resp.get("Item")
    return dec_to_native(item) if item else None


def scan_eq(table, **attrs) -> list[dict]:
    """Scan a table returning rows where every given attribute equals its value.

    Tables in this app are small demo tables, so a filtered scan is acceptable
    for test verification purposes.
    """
    if table is None:
        return []
    filter_expr = None
    for key, value in attrs.items():
        cond = Attr(key).eq(value)
        filter_expr = cond if filter_expr is None else filter_expr & cond

    items: list[dict] = []
    kwargs = {"FilterExpression": filter_expr} if filter_expr is not None else {}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return [dec_to_native(i) for i in items]


def count_items(table) -> int:
    """Return the live item count of a table via a paginated COUNT scan."""
    if table is None:
        return -1
    total = 0
    kwargs = {"Select": "COUNT"}
    while True:
        resp = table.scan(**kwargs)
        total += resp.get("Count", 0)
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return total


def wait_until(predicate, timeout: float = 10.0, interval: float = 1.0) -> bool:
    """Poll ``predicate()`` until it returns True or the timeout expires.

    Gives DynamoDB writes triggered by the API a moment to become visible
    before a verification is declared failed.
    """
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def row_summary(row: dict | None, fields: list[str]) -> str:
    """Render selected fields of a row as a compact one-line summary."""
    if row is None:
        return "(no row)"
    return ", ".join(f"{f}={row.get(f)!r}" for f in fields)


def make_check(
    table_alias: str,
    expectation: str,
    passed: bool,
    before: str = "",
    after: str = "",
) -> DbCheck:
    """Build a DbCheck record for the report."""
    return DbCheck(
        table=table_alias,
        expectation=expectation,
        before=before,
        after=after,
        passed=passed,
    )

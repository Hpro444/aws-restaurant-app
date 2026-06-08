"""Shared date/period and delta utilities for report services."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def parse_date(value: str) -> date:
    """Parse a ``"YYYY-MM-DD"`` or ISO-8601 UTC string to a UTC ``date``."""
    if len(value) == 10:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).date()


def period_start_for(dt: date) -> date:
    """Return the Monday of the ISO week containing ``dt``."""
    return dt - timedelta(days=dt.weekday())


def period_end_for(start: date) -> date:
    """Return the Sunday of the week that starts on ``start``."""
    return start + timedelta(days=6)


def pct_delta(
    current: float | int | None, previous: float | int | None
) -> float | None:
    """Return ``(current - previous) / previous * 100`` rounded to 2 dp, or None."""
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)

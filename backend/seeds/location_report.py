"""Seed module for location comparison reports."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from commons.report_utils import pct_delta  # type: ignore[import-not-found]
from domain.location_report import LocationReport  # type: ignore[import-not-found]
from enums.reservation_status import ReservationStatus  # type: ignore[import-not-found]

from seeds.utils import seed_id, to_item


def _period_start(d: date) -> date:
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _period_end(start: date) -> date:
    """Return the Sunday of the week starting on start."""
    return start + timedelta(days=6)


def _as_date(dt) -> date:
    """Extract a ``date`` from a ``datetime`` or return ``dt`` unchanged if already a ``date``."""
    return dt.date() if isinstance(dt, datetime) else dt


def _seed_period_reports(
    p_start: date,
    p_end: date,
    locations: dict,
    waiters: dict,
    reservations: list,
    orders: list,
    dishes: list,
    feedbacks: list,
) -> list[LocationReport]:
    """Compute one LocationReport per location for the given ISO week.

    Aggregates only data whose date falls within [p_start, p_end]:

    * ``orders_processed`` — orders linked to FINISHED reservations in the period.
    * ``revenue``          — sum of (quantity × dish price) for in-period orders.
    * ``cuisine_feedback_*`` — cuisine feedback entries in the period.

    Args:
        p_start: Monday of the target ISO week.
        p_end: Sunday of the target ISO week.
        locations: UUID-keyed dict of Location objects.
        waiters: Email-keyed dict of Waiter objects (used to map order → location).
        reservations: All seeded Reservation objects.
        orders: All seeded Order objects.
        dishes: All seeded Dish objects.
        feedbacks: All seeded FeedbackCuisine objects.

    Returns:
        The list of LocationReport objects for the period (not yet persisted).

    """
    period_finished_ids = {
        r.id
        for r in reservations
        if r.status == ReservationStatus.FINISHED
        and p_start <= _as_date(r.created_at) <= p_end
    }

    dish_price_by_id = {d.id: d.price for d in dishes}
    waiter_location_by_id = {w.id: w.location_id for w in waiters.values()}

    orders_by_location: dict = {}
    for order in orders:
        if order.reservation_id not in period_finished_ids:
            continue
        location_id = waiter_location_by_id.get(order.waiter_id)
        if location_id is not None:
            orders_by_location.setdefault(location_id, []).append(order)

    feedbacks_by_location: dict = {}
    for fb in feedbacks:
        fb_date = _as_date(fb.date)
        if p_start <= fb_date <= p_end:
            feedbacks_by_location.setdefault(fb.location_id, []).append(fb)

    reports: list[LocationReport] = []
    for location_id, location in locations.items():
        loc_orders = orders_by_location.get(location_id, [])
        loc_feedbacks = feedbacks_by_location.get(location_id, [])

        orders_processed = len(loc_orders)
        revenue = sum(
            item.quantity * dish_price_by_id.get(item.dish_id, 0.0)
            for order in loc_orders
            for item in order.items
        )

        fb_count = len(loc_feedbacks)
        fb_sum = float(sum(f.rate for f in loc_feedbacks if f.rate is not None))
        avg_fb = round(fb_sum / fb_count, 2) if fb_count else None
        min_fb = min(
            (f.rate for f in loc_feedbacks if f.rate is not None), default=None
        )

        reports.append(
            LocationReport(
                id=seed_id("location_report", f"{location_id}:{p_start.isoformat()}"),
                location_id=location_id,
                location_name=location.name,
                report_period_start=p_start.isoformat(),
                report_period_end=p_end.isoformat(),
                orders_processed=orders_processed,
                cuisine_feedback_count=fb_count,
                cuisine_feedback_sum=fb_sum,
                avg_cuisine_feedback=avg_fb,
                min_cuisine_feedback=min_fb,
                revenue=revenue,
            )
        )

    return reports


def _seed_random_week(
    week_offset: int,
    locations: dict,
) -> list[LocationReport]:
    """Build one random LocationReport per location for a past week.

    Uses a deterministic per-location RNG seed for reproducibility.

    Args:
        week_offset: How many ISO weeks back from the current Monday.
        locations: UUID-keyed dict of Location objects.

    Returns:
        The list of LocationReport objects for the period (not yet persisted).

    """
    today = date.today()
    curr_monday = today - timedelta(days=today.weekday())
    p_start = curr_monday - timedelta(weeks=week_offset)
    p_end = p_start + timedelta(days=6)

    reports: list[LocationReport] = []
    for location_id, location in locations.items():
        rng = random.Random(f"{location_id}:{week_offset}")

        orders_processed = rng.randint(20, 80)
        revenue = round(rng.uniform(500.0, 3500.0), 2)
        fb_count = rng.randint(2, 18)
        rates = [rng.randint(2, 5) for _ in range(fb_count)]
        fb_sum = float(sum(rates))
        avg_fb = round(fb_sum / fb_count, 2)
        min_fb = min(rates)

        reports.append(
            LocationReport(
                id=seed_id("location_report", f"{location_id}:{p_start.isoformat()}"),
                location_id=location_id,
                location_name=location.name,
                report_period_start=p_start.isoformat(),
                report_period_end=p_end.isoformat(),
                orders_processed=orders_processed,
                cuisine_feedback_count=fb_count,
                cuisine_feedback_sum=fb_sum,
                avg_cuisine_feedback=avg_fb,
                min_cuisine_feedback=min_fb,
                revenue=revenue,
            )
        )

    return reports


def _apply_deltas(reports: list[LocationReport]) -> None:
    """Populate the ``*_delta_pct`` fields in place across all seeded weeks.

    Mirrors the live data-capture lambda: each report's delta is the percentage
    change versus the same location's report for the immediately preceding ISO
    week, or ``None`` when no such row exists or the previous value is zero/None.

    Args:
        reports: Every LocationReport built for all seeded weeks (any order).

    """
    by_key = {(r.location_id, r.report_period_start): r for r in reports}
    for report in reports:
        prev_start = (
            date.fromisoformat(report.report_period_start) - timedelta(days=7)
        ).isoformat()
        prev = by_key.get((report.location_id, prev_start))
        if prev is None:
            continue
        report.orders_processed_delta_pct = pct_delta(
            report.orders_processed, prev.orders_processed
        )
        report.avg_cuisine_feedback_delta_pct = pct_delta(
            report.avg_cuisine_feedback, prev.avg_cuisine_feedback
        )
        report.revenue_delta_pct = pct_delta(report.revenue, prev.revenue)


def _backfill_oldest_deltas(reports: list[LocationReport]) -> None:
    """Set plausible random deltas on the oldest seeded week (week offset 3).

    ``_apply_deltas`` leaves these as ``None`` because no week-4 row exists.
    A deterministic-random value per location keeps the UI looking complete.

    Args:
        reports: Every LocationReport built for all seeded weeks (any order).

    """
    oldest_start = min(r.report_period_start for r in reports)
    for report in reports:
        if report.report_period_start != oldest_start:
            continue
        rng = random.Random(f"{report.location_id}:oldest_delta")
        report.orders_processed_delta_pct = round(rng.uniform(-20.0, 25.0), 2)
        report.avg_cuisine_feedback_delta_pct = round(rng.uniform(-15.0, 20.0), 2)
        report.revenue_delta_pct = round(rng.uniform(-18.0, 22.0), 2)


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed LocationReport rows for the current ISO week and three past random weeks.

    One real-aggregated row per location (current week) and three rows with
    realistic random data (weeks 1–3 ago) are written, giving the API four
    rows per location with fully-populated delta percentages.

    Requires context['locations'], context['waiters'], context['reservations'],
    context['orders'], context['dishes'], and context['feedback_cuisine'].
    """
    report_table = dynamodb.Table(tables["location_report"])

    locations = context.get("locations", {})
    waiters = context.get("waiters", {})
    reservations = context.get("reservations", [])
    orders = context.get("orders", [])
    dishes = context.get("dishes", [])
    feedbacks = context.get("feedback_cuisine", [])

    today = date.today()
    curr_start = _period_start(today)
    curr_end = _period_end(curr_start)

    curr_reports = _seed_period_reports(
        curr_start,
        curr_end,
        locations,
        waiters,
        reservations,
        orders,
        dishes,
        feedbacks,
    )

    past_reports: list[LocationReport] = []
    for week_offset in range(1, 4):
        past_reports.extend(_seed_random_week(week_offset, locations))

    all_reports = curr_reports + past_reports
    _apply_deltas(all_reports)
    _backfill_oldest_deltas(all_reports)

    with report_table.batch_writer() as batch:
        for report in all_reports:
            batch.put_item(Item=to_item(report))

    context["location_reports"] = all_reports

    print(
        f"  ✓ Seeded {len(curr_reports)} location reports "
        f"(current week {curr_start} → {curr_end}) + "
        f"{len(past_reports)} random past rows (weeks 1–3)"
    )

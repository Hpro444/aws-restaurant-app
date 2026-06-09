"""Seed module for waiter performance reports."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from commons.report_utils import pct_delta  # type: ignore[import-not-found]
from domain.waiter_report import WaiterReport  # type: ignore[import-not-found]
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
    waiters: dict,
    reservations: list,
    orders: list,
    slots: list,
    locations: dict,
    feedbacks: list,
) -> list[WaiterReport]:
    """Compute one WaiterReport per waiter for the given ISO week.

    Aggregates only data whose date falls within [p_start, p_end]:

    * ``orders_processed`` — orders linked to FINISHED reservations in the period.
    * ``working_hours``    — slots in the period × 1.75 h each.
    * ``service_feedback_count/sum/avg/min`` — service feedback entries in the period.

    Args:
        p_start: Monday of the target ISO week.
        p_end: Sunday of the target ISO week.
        waiters: Email-keyed dict of Waiter domain objects.
        reservations: All seeded Reservation objects.
        orders: All seeded Order objects.
        slots: All seeded Slot objects.
        locations: UUID-keyed dict of Location objects.
        feedbacks: All seeded FeedbackService objects.

    Returns:
        The list of WaiterReport objects for the period (not yet persisted).

    """
    period_finished_ids = {
        r.id
        for r in reservations
        if r.status == ReservationStatus.FINISHED
        and p_start <= _as_date(r.created_at) <= p_end
    }

    orders_by_waiter: dict = {}
    for order in orders:
        if order.reservation_id in period_finished_ids:
            orders_by_waiter.setdefault(order.waiter_id, []).append(order)

    feedbacks_by_waiter: dict = {}
    for fb in feedbacks:
        fb_date = _as_date(fb.date)
        if p_start <= fb_date <= p_end:
            feedbacks_by_waiter.setdefault(fb.waiter_id, []).append(fb)

    slots_by_waiter: dict = {}
    for slot in slots:
        if slot.waiter_id is None:
            continue
        slot_date = _as_date(slot.date)
        if p_start <= slot_date <= p_end:
            slots_by_waiter.setdefault(slot.waiter_id, []).append(slot)

    reports: list[WaiterReport] = []
    for waiter in waiters.values():
        w_orders = orders_by_waiter.get(waiter.id, [])
        w_feedbacks = feedbacks_by_waiter.get(waiter.id, [])
        w_slots = slots_by_waiter.get(waiter.id, [])

        orders_processed = len(w_orders)
        unique_starts = {slot.start_time for slot in w_slots}
        working_hours = len(unique_starts) * 1.75

        fb_count = len(w_feedbacks)
        fb_sum = float(sum(f.rate for f in w_feedbacks if f.rate is not None))
        avg_fb = round(fb_sum / fb_count, 2) if fb_count else None
        min_fb = min((f.rate for f in w_feedbacks if f.rate is not None), default=None)

        location = locations.get(waiter.location_id)
        location_name = location.name if location else ""

        reports.append(
            WaiterReport(
                id=seed_id("waiter_report", f"{waiter.id}:{p_start.isoformat()}"),
                waiter_id=waiter.id,
                location_id=waiter.location_id,
                location_name=location_name,
                waiter_first_name=waiter.fname,
                waiter_last_name=waiter.lname,
                waiter_email=waiter.email,
                report_period_start=p_start.isoformat(),
                report_period_end=p_end.isoformat(),
                working_hours=working_hours,
                orders_processed=orders_processed,
                service_feedback_count=fb_count,
                service_feedback_sum=fb_sum,
                avg_service_feedback=avg_fb,
                min_service_feedback=min_fb,
            )
        )

    return reports


def _seed_random_week(
    week_offset: int,
    waiters: dict,
    locations: dict,
) -> list[WaiterReport]:
    """Build one random WaiterReport per waiter for a past week.

    Uses a deterministic per-waiter RNG seed so results are reproducible
    across runs while still looking like real varied data.

    Args:
        week_offset: How many ISO weeks back from the current Monday.
        waiters: Email-keyed dict of Waiter domain objects.
        locations: UUID-keyed dict of Location objects.

    Returns:
        The list of WaiterReport objects for the period (not yet persisted).

    """
    today = date.today()
    curr_monday = today - timedelta(days=today.weekday())
    p_start = curr_monday - timedelta(weeks=week_offset)
    p_end = p_start + timedelta(days=6)

    reports: list[WaiterReport] = []
    for waiter in waiters.values():
        rng = random.Random(f"{waiter.id}:{week_offset}")

        orders_processed = rng.randint(5, 30)
        working_hours = round(rng.uniform(10.5, 42.0), 1)
        fb_count = rng.randint(1, 10)
        rates = [rng.randint(2, 5) for _ in range(fb_count)]
        fb_sum = float(sum(rates))
        avg_fb = round(fb_sum / fb_count, 2)
        min_fb = min(rates)

        location = locations.get(waiter.location_id)
        location_name = location.name if location else ""

        reports.append(
            WaiterReport(
                id=seed_id("waiter_report", f"{waiter.id}:{p_start.isoformat()}"),
                waiter_id=waiter.id,
                location_id=waiter.location_id,
                location_name=location_name,
                waiter_first_name=waiter.fname,
                waiter_last_name=waiter.lname,
                waiter_email=waiter.email,
                report_period_start=p_start.isoformat(),
                report_period_end=p_end.isoformat(),
                working_hours=working_hours,
                orders_processed=orders_processed,
                service_feedback_count=fb_count,
                service_feedback_sum=fb_sum,
                avg_service_feedback=avg_fb,
                min_service_feedback=min_fb,
            )
        )

    return reports


def _apply_deltas(reports: list[WaiterReport]) -> None:
    """Populate the ``*_delta_pct`` fields in place across all seeded weeks.

    Mirrors the live data-capture lambda: each report's delta is the percentage
    change versus the same waiter's report for the immediately preceding ISO week,
    or ``None`` when no such row exists or the previous value is zero/None.

    Args:
        reports: Every WaiterReport built for all seeded weeks (any order).

    """
    by_key = {(r.waiter_id, r.report_period_start): r for r in reports}
    for report in reports:
        prev_start = (
            date.fromisoformat(report.report_period_start) - timedelta(days=7)
        ).isoformat()
        prev = by_key.get((report.waiter_id, prev_start))
        if prev is None:
            continue
        report.orders_processed_delta_pct = pct_delta(
            report.orders_processed, prev.orders_processed
        )
        report.avg_service_feedback_delta_pct = pct_delta(
            report.avg_service_feedback, prev.avg_service_feedback
        )


def _backfill_oldest_deltas(reports: list[WaiterReport]) -> None:
    """Set plausible random deltas on the oldest seeded week (week offset 3).

    ``_apply_deltas`` leaves these as ``None`` because no week-4 row exists.
    A deterministic-random value per waiter keeps the UI looking complete.

    Args:
        reports: Every WaiterReport built for all seeded weeks (any order).

    """
    oldest_start = min(r.report_period_start for r in reports)
    for report in reports:
        if report.report_period_start != oldest_start:
            continue
        rng = random.Random(f"{report.waiter_id}:oldest_delta")
        report.orders_processed_delta_pct = round(rng.uniform(-20.0, 25.0), 2)
        report.avg_service_feedback_delta_pct = round(rng.uniform(-15.0, 20.0), 2)


def seed(dynamodb, tables: dict, context: dict) -> None:
    """Seed WaiterReport rows for the current ISO week and three past random weeks.

    One real-aggregated row per waiter (current week) and three rows with
    realistic random data (weeks 1–3 ago) are written, giving the API four
    rows per waiter with fully-populated delta percentages.

    Requires context['waiters'], context['reservations'], context['orders'],
    context['slots'], context['locations'], and context['feedback_service'].
    """
    report_table = dynamodb.Table(tables["waiter_report"])

    waiters = context.get("waiters", {})
    reservations = context.get("reservations", [])
    orders = context.get("orders", [])
    slots = context.get("slots", [])
    locations = context.get("locations", {})
    feedbacks = context.get("feedback_service", [])

    today = date.today()
    curr_start = _period_start(today)
    curr_end = _period_end(curr_start)

    curr_reports = _seed_period_reports(
        curr_start,
        curr_end,
        waiters,
        reservations,
        orders,
        slots,
        locations,
        feedbacks,
    )

    past_reports: list[WaiterReport] = []
    for week_offset in range(1, 4):
        past_reports.extend(_seed_random_week(week_offset, waiters, locations))

    all_reports = curr_reports + past_reports
    _apply_deltas(all_reports)
    _backfill_oldest_deltas(all_reports)

    with report_table.batch_writer() as batch:
        for report in all_reports:
            batch.put_item(Item=to_item(report))

    context["waiter_reports"] = all_reports

    print(
        f"  ✓ Seeded {len(curr_reports)} waiter reports "
        f"(current week {curr_start} → {curr_end}) + "
        f"{len(past_reports)} random past rows (weeks 1–3)"
    )

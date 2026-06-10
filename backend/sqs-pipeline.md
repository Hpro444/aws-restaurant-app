# Report: SQS Event Pipeline & Report Calculation (`feature/data_capture_lambda`)

## 1. High-level architecture

The branch adds an **asynchronous, event-driven analytics pipeline** on top of the existing synchronous API. The flow is:

```
                                  (HTTP request)
  Customer / Waiter ──▶ api-handler Lambda ──▶ writes to DynamoDB (source of truth)
                                   │
                                   │  best-effort publish (JSON, camelCase)
                                   ▼
                          ┌──────────────────┐
                          │  SQS: event_queue │   (single standard queue)
                          └──────────────────┘
                                   │  sqs_trigger, batch_size = 1
                                   ▼
                        data_capture_lambda  (consumer)
                                   │  dispatches each record to BOTH:
                          ┌────────┴─────────┐
                          ▼                  ▼
              WaiterReportService   LocationReportService
                          │                  │
                          ▼                  ▼
              waiter-report table    location-report table
              (one row per             (one row per
               waiter × ISO-week)       location × ISO-week)
```

There is **one queue** carrying **two kinds of message** (reservation events and feedback events), and **one consumer Lambda** that fans each message out to two services. Reports are weekly read-models keyed by ISO week.

---

## 2. Infrastructure wiring

**The queue** — `restaurant-backend-app/deployment_resources.json:48`:
- `event_queue`, **standard** queue (`fifo_queue: false`) — no ordering guarantee, at-least-once delivery.
- `visibility_timeout: 600`s, `message_retention_period: 345600`s (4 days), `maximum_message_size: 262144` (256 KB).
- **No DLQ and no redrive policy configured** (see Risks §8).

**The consumer trigger** — `lambdas/data_capture_lambda/lambda_config.json:12`:
```json
"event_sources": [{ "resource_type": "sqs_trigger", "target_queue": "event_queue",
                    "batch_size": 1, "enabled": true }]
```
- `batch_size: 1` → each Lambda invocation handles **exactly one** SQS message.
- Runtime python3.13, 128 MB, 100 s timeout. IAM role grants `sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes` plus DynamoDB read/write.
- It receives the queue URL via env var `EVENT_QUEUE_URL = ${event_queue_url}`, plus all the table aliases it needs to recompute reports.

**The producer** — the `api-handler` Lambda holds the same `EVENT_QUEUE_URL` and a single `SqsService` instance shared across the booking, reservation-management, and feedback services (`lambdas/api-handler/handler.py:77-83`).

---

## 3. When do events get published? (Producer side)

`SqsService.publish()` (`services/sqs_service.py:41`) is **payload-agnostic**: it serializes any Pydantic model with `model_dump_json(by_alias=True)` (→ camelCase) and `send_message`s it. Two safety properties:
- If `queue_url` is empty (local dev / unit tests) the publish is **silently skipped**.
- All boto3/serialization exceptions are **caught and logged** internally — SQS failures never break the HTTP response.

On top of that internal swallowing, **every caller also wraps the publish in its own `try/except`** (matching the team convention that mock-injected `SqsService` bypasses the internal swallow). So publishing is best-effort at two layers.

There are exactly **5 publish sites**, all on the API path:

| Trigger | Source | Event produced |
|---|---|---|
| Create a booking | `booking_service.py:204` | `ReservationEventMessage(eventType=CREATED)` |
| Update a reservation | `reservation_management_service.py:214` | `FINISHED` if the new status is `FINISHED`, else `UPDATED` |
| Cancel a reservation | `reservation_management_service.py:254` | `ReservationEventMessage(eventType=CANCELLED)` |
| Leave **service** feedback | `feedback_service.py:262` | `FeedbackEventMessage(feedbackType="service")` |
| Leave **culinary** feedback | `feedback_service.py:324` | `FeedbackEventMessage(feedbackType="culinary")` |

The publish always happens **after** the DynamoDB write succeeds, so the queue never carries an event for data that wasn't persisted. The event envelopes are *flat* (all fields inlined, no nesting) — `dto/reservation_event.py` and `dto/feedback_event.py`. Both DTOs use `populate_by_name=True` + aliases + `extra="ignore"`, so they round-trip camelCase on the wire and tolerate unknown fields.

---

## 4. How the consumer dispatches (data_capture_lambda)

`lambdas/data_capture_lambda/handler.py:29`:

```python
for record in records:
    try:
        body = json.loads(record.get("body", "{}"))
        if "feedbackId" in body:
            msg = FeedbackEventMessage.model_validate(body)
            self._waiter_report_service.handle_feedback_event(msg)
            self._location_report_service.handle_feedback_event(msg)
        else:
            msg = ReservationEventMessage.model_validate(body)
            self._waiter_report_service.handle_reservation_event(msg)
            self._location_report_service.handle_reservation_event(msg)
        processed += 1
    except Exception:
        _LOG.error("Failed to process SQS record", exc_info=True, record=record)
```

Key behaviors:
- **Message-type discrimination is by key presence**: if the JSON body contains `feedbackId` it's a feedback event, otherwise a reservation event. (Reservation messages never carry `feedbackId`.)
- **Every message is sent to *both* services.** Each service then independently decides whether the message is relevant to it (§5). This is deliberate: "one malformed message does not abort the rest of the batch."
- The services are constructed once at **cold start** (`__init__`), so repositories/clients are reused across warm invocations.
- The per-record `try/except` means a single bad record is logged and skipped; the handler always returns `200 {"processed": N}`. With `batch_size: 1` this means **the message is acknowledged and deleted even if processing threw** — see Risks §8.

---

## 5. Relevance filtering — which events actually change a report

Each event is delivered to both services, but each service acts only on the subset it cares about:

| Service | Reservation event | Feedback event |
|---|---|---|
| **WaiterReportService** | only `FINISHED` **and** `waiter_id` present (`waiter_report_service.py:76-79`) | only `feedbackType == "service"` **and** `waiter_id` present (`:92-95`) |
| **LocationReportService** | only `FINISHED` **and** `location_id` present (`location_report_service.py:78-81`) | only `feedbackType == "culinary"` **and** `location_id` present (`:94-97`) |

Consequences:
- `CREATED`, `UPDATED`, `CANCELLED` reservation events are **published but produce no report change** — only `FINISHED` reservations drive orders/revenue/working-hours. (The non-FINISHED events exist for other potential consumers / completeness.)
- **Service** feedback only moves the waiter report; **culinary** feedback only moves the location report. A culinary feedback message still reaches `WaiterReportService.handle_feedback_event`, which immediately returns because the type isn't `service`.

---

## 6. The weekly period model

All period math lives in `commons/report_utils.py`:
- `parse_date(value)` accepts either `"YYYY-MM-DD"` or a full ISO-8601 UTC timestamp (strips `Z`, converts to UTC, takes `.date()`).
- `period_start_for(dt)` = the **Monday** of `dt`'s ISO week (`dt - timedelta(days=dt.weekday())`).
- `period_end_for(start)` = `start + 6 days` = the **Sunday**.

So every report row is identified by `(entity_id, report_period_start=Monday)` and stores both Monday and Sunday as ISO strings.

**Which date is used to pick the week?**
- **Reservation events:** the reservation's own `date` field (`parse_date(msg.date)`).
- **Feedback events:** the **reservation's dining week**, not the feedback submission date. `_resolve_feedback_period_date()` (identical in both services) loads the reservation via `reservation_id` and uses `reservation.date`; only if that lookup fails does it fall back to `msg.timestamp[:10]`. This keeps all metrics for one reservation — its orders, revenue, and feedback — in the same weekly row.

---

## 7. How each report is calculated (full recompute on every event)

The crucial design property: **every relevant event triggers a complete recalculation of the affected `(entity, week)` row from the database** — it does not incrementally add to existing counters. This makes processing **idempotent and order-independent**: replays, duplicate SQS deliveries, and out-of-order messages all converge to the same correct row.

### 7a. WaiterReport (`waiter_report_service.py:115` `_upsert_report`)

For `(waiter_id, week)`:
1. Load `waiter`; load its `location`. If either is missing → log warning and **skip** (no row written).
2. **Working hours**: `slots = slot_repo.find_by_waiter_id_and_period(waiter, start, end)`; `working_hours = len(slots) * 1.75`. (1.75 h per slot — see Risks §8 re: this magic number vs. the 90-minute slot.)
3. **Orders processed**: all reservations for the waiter in the period; keep those with `status == FINISHED`; `orders_processed = Σ len(orders for each finished reservation)`.
4. **Service feedback**: `feedbacks = feedback_service_repo.find_by_waiter_id_and_period(...)`:
   - `service_feedback_count = len(feedbacks)`
   - `service_feedback_sum = Σ rate`
   - `avg_service_feedback = round(sum/count, 2)` or `None` if no feedback
   - `min_service_feedback = min(rate)` or `None`
5. **Deltas** (§7c) against the previous week's persisted row.
6. **Upsert**: reuse the existing row's `id` if one exists for this week, otherwise mint a fresh `uuid4`; then `update()` (PutItem-style upsert).

### 7b. LocationReport (`location_report_service.py:117` `_upsert_report`)

For `(location_id, week)`:
1. Load `location` (skip if missing).
2. Gather **all waiters** at the location; for each, fetch its reservations in the period; collect the IDs of all `FINISHED` ones across every waiter.
3. **Orders + revenue** via `_collect_orders_and_revenue(finished_ids)` (`:197`):
   - For each finished reservation, fetch its orders; `orders_processed += len(orders)`.
   - For each order line item: `revenue += item.quantity * dish_price`, where `dish_price` comes from the dish catalogue (a per-call `dish_price_cache` avoids repeated lookups; a missing dish prices at `0.0`).
4. **Cuisine feedback**: `feedback_cuisine_repo.find_by_location_id_and_period(...)` → count / sum / `avg_cuisine_feedback` (2dp or None) / `min_cuisine_feedback`.
5. **Deltas** (§7c).
6. **Upsert** with existing-or-new `uuid4` id.

Both report tables key on `id` (PK) and expose a `*_period_index` GSI (PK = entity_id, SK = `report_period_start`) used both to find the current week's row and to fetch the previous week's row.

### 7c. Delta calculation — the "vs. last week" percentages

`pct_delta(current, previous)` (`report_utils.py:25`):

```python
(current - previous) / previous * 100, rounded to 2 dp
→ None if current is None, previous is None, or previous == 0
```

How "previous" is obtained: take this week's Monday, subtract 7 days, snap back to that week's Monday, and **read the previously persisted report row** for that week via the GSI:

```python
prev_period_start = period_start_for(period_start - timedelta(days=7)).isoformat()
prev = repo.find_by_..._and_period(entity_id, prev_period_start)
```

Deltas computed:
- **WaiterReport**: `orders_processed_delta_pct` (vs prev `orders_processed`), `avg_service_feedback_delta_pct` (vs prev `avg_service_feedback`).
- **LocationReport**: `orders_processed_delta_pct`, `avg_cuisine_feedback_delta_pct`, `revenue_delta_pct`.

Important nuances of the delta model:
- The delta is computed against the **stored value of the previous week's row**, not a fresh recomputation of last week. If last week's row doesn't exist (no events landed there), `prev is None` → all deltas are `None`, even if there was real prior-week activity.
- A delta is only refreshed when the **current** week receives an event. If last week's numbers later change (a late `FINISHED` event for last week), this week's already-written delta is **not** retroactively recalculated.
- `previous == 0` yields `None` (avoids divide-by-zero), so going from 0 → N shows no percentage.

---

## 8. Observations, edge cases & risks

1. **No DLQ + swallowed consumer exceptions = silent data loss on poison messages.** The handler catches every per-record exception, logs it, and still returns success, so SQS deletes the message. A message that consistently fails to process (bad UUID, schema drift, transient DynamoDB error at the wrong moment) is **dropped, not retried**. Because `batch_size: 1`, there's no partial-batch-failure concern, but there is also no safety net. Consider a redrive policy + DLQ, or re-raising so SQS retries.

2. **Best-effort publish means events can be missed.** If the SQS `send_message` fails (or the queue URL is unset), the API still returns 200 and the report simply never updates for that action. Acceptable for analytics, but reports can silently drift from the source tables.

3. **Delta is row-to-row, not recomputed.** As noted in §7c, deltas can be `None` or stale depending on whether neighboring weekly rows exist and the order in which weeks receive events. Reports are eventually-consistent per-week but the cross-week deltas are point-in-time snapshots.

4. **`working_hours = len(slots) * 1.75`** is a magic constant. Given the project rule that slots are fixed 90-minute (1.5 h) blocks, 1.75 appears to bake in turnover/gap time. Worth a named constant + comment; it's currently unexplained in the code.

5. **Location recompute can be expensive.** Every relevant event re-reads *all* waiters at the location, *all* their period reservations, *all* orders, and prices *all* line items. At scale this is O(waiters × reservations × orders × items) per single message, with `batch_size: 1` (one invocation per message). Fine for a course/demo dataset; a hotspot if volume grows.

6. **Extra reservation lookup per feedback** to resolve the dining week. Low cost, but it means a feedback whose reservation is missing falls back to the *submission* timestamp's week — which could place it in a different week than the reservation's other metrics.

7. **Type discrimination by key presence** (`"feedbackId" in body`) is implicit. It works because the two envelopes are disjoint, but a future field rename would silently misroute messages. The explicit `eventType` field is *not* used for routing.

8. **Idempotency is the strong point.** Because each event fully recomputes from the DB and upserts on a deterministic `(entity, week)` row (reusing the existing `id`), at-least-once delivery, duplicates, and reordering are all handled correctly — the main reason the full-recompute approach was chosen over incremental counters.

---

## 9. One-line summary of the trigger lifecycle

A booking/feedback API call writes to DynamoDB, then best-effort publishes a flat JSON event to the single `event_queue`; the `data_capture_lambda` consumes one message at a time, routes it to both report services, each of which — only for `FINISHED` reservations and its own feedback type — recomputes the entire weekly row for the affected waiter/location from the database, computes percentage deltas against the previously stored prior-week row, and upserts the result, making the whole pipeline idempotent and order-independent.

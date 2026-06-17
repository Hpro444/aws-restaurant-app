# automation-qa — End-to-End API Tests

Automated end-to-end tests for every API route of the restaurant backend, run against a real deployed AWS environment. Each step records the request sent, the response received, an HTTP assertion, and a before/after DynamoDB verification, then renders everything into a formatted **`test_output.pdf`** report.

---

## Layout

```
automation-qa/
├── run_e2e.sh / run_e2e.ps1   # full pipeline: deploy → seed → test → clean
├── test_e2e_endpoints.py      # orchestrator (creds → seed → suites → PDF)
├── e2e/                       # modular suites, one per route group
│   ├── __init__.py            # SUITE_ORDER (mirrors seeds.SEED_ORDER)
│   ├── auth.py                # sign-up, sign-in, refresh, logout
│   ├── locations.py           # locations list, detail, slot times, select-options
│   ├── dishes.py              # dishes list, popular, by id
│   ├── users.py               # user profile get/update, waiter location
│   ├── customers.py           # customers list (waiter-only)
│   ├── reports.py             # admin reports endpoint
│   ├── bookings.py            # table availability and reservation CRUD
│   ├── orders.py              # order creation (waiter-only)
│   ├── waiter_reservations.py # waiter table-filtered reservation view
│   ├── bookings_lifecycle.py  # full booking state-machine walkthrough
│   ├── feedbacks.py           # feedback submit, update, context, paginated list
│   ├── sqs.py                 # SQS-triggered report recalculation (T-1 through T-12)
│   ├── http_client.py         # request executor + result recording
│   ├── db.py                  # DynamoDB snapshot / polling helpers
│   ├── recorder.py            # step recording model
│   ├── context.py             # shared run context (tokens, ids, config)
│   ├── config.py              # environment resolution helpers
│   └── report.py              # test_output.pdf generation
├── ids.json / tokens.json     # written by the seeder (gitignored)
├── logs/                      # per-run console log + results JSON (gitignored)
└── test_output.pdf            # report produced by each run
```

### Suite execution order

Suites run in `SUITE_ORDER` — later suites depend on entities created by earlier ones:

```
auth → locations → dishes → users → customers → reports →
bookings → orders → waiter_reservations → bookings_lifecycle → feedbacks → sqs
```

### Debug artifacts

Every run writes two files into `logs/`:

- `e2e_<timestamp>.log` — full console output (ANSI-stripped), including every request, response, and DB diff.
- `e2e_<timestamp>_results.json` — machine-readable dump of every step for post-mortem diffing.

---

## Running the full pipeline (recommended)

```powershell
.\run_e2e.ps1     # Windows
./run_e2e.sh      # Linux / macOS / Git Bash
```

The scripts:

1. **Validate AWS credentials** — abort with an error when invalid/expired.
2. Patch `backend/restaurant-backend-app/.syndicate-config-dev/syndicate.yml` to the dedicated e2e values (`deploy_target_bucket: .../e2e`, `resources_suffix: -dev1`) — **only for the duration of the run**; the original file is restored at the end no matter what.
3. `syndicate clean` → `syndicate build` → `syndicate deploy`.
4. Run `test_e2e_endpoints.py` (which seeds first).
5. `syndicate clean` to tear the e2e environment down.

---

## Running just the tests

```bash
uv run --project ../backend python test_e2e_endpoints.py              # seed + test
uv run --project ../backend python test_e2e_endpoints.py --skip-seed  # reuse existing seed data
uv run --project ../backend python test_e2e_endpoints.py --check-creds
```

The orchestrator validates credentials, runs `backend/quick_seed.py` (which writes `ids.json` and `tokens.json` into this directory via `E2E_ARTIFACTS_DIR`), resolves the API Gateway URL and real DynamoDB table names at runtime, executes every suite in `SUITE_ORDER`, prints a colored console summary, and writes `test_output.pdf`.

---

## Requirements

- `uv` installed; dependencies come from `backend/pyproject.toml` (`uv sync` in `backend/` once).
- Valid AWS credentials: syndicate temp credentials in `syndicate.yml` or an active `aws sso login` session.
- A deployed environment (the run scripts deploy one themselves; use `--skip-seed` to skip re-seeding when re-running against an existing deployment).

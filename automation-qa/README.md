# automation-qa — End-to-End API Tests

Automated end-to-end tests for **every API route** of the restaurant backend,
run against a real deployed AWS environment. Each step records the request
sent, the response received, an HTTP assertion, and a before/after DynamoDB
verification, then renders everything into a formatted **`test_output.pdf`**
report.

## Layout

```
automation-qa/
├── run_e2e.sh / run_e2e.ps1   # full pipeline: deploy → seed → test → clean
├── test_e2e_endpoints.py      # orchestrator (creds → seed → suites → PDF)
├── e2e/                       # modular suites, one per route group
│   ├── __init__.py            # SUITE_ORDER (like seeds.SEED_ORDER)
│   ├── auth.py … feedbacks.py # suites, each exposing run(ctx)
│   ├── http_client.py         # request executor + result recording
│   ├── db.py                  # DynamoDB snapshot/polling helpers
│   └── report.py              # test_output.pdf generation
├── ids.json / tokens.json     # written here by the seeder (gitignored)
├── logs/                      # per-run console log + results JSON (gitignored)
└── test_output.pdf            # the report produced by each run
```

Every run writes two debug artifacts into `logs/`:

- `e2e_<timestamp>.log` — the full console output (ANSI-stripped), including
  every request, response, and DB diff.
- `e2e_<timestamp>_results.json` — machine-readable dump of every step
  (request, response body, HTTP assertion, DB checks) for post-mortem diffing.

## Running the full pipeline (recommended)

```powershell
.\run_e2e.ps1     # Windows
./run_e2e.sh      # Linux / macOS / Git Bash
```

The scripts:

1. **Validate AWS credentials** — abort with an error when invalid/expired.
2. Patch `backend/restaurant-backend-app/.syndicate-config-dev/syndicate.yml`
   to the dedicated e2e values (`deploy_target_bucket:
   run26-tm3-project-education-artifacts-dev/e2e`, `resources_suffix: -dev1`)
   — **only for the duration of the run**; the original file is restored at
   the end no matter what.
3. `syndicate clean` → `syndicate build` → `syndicate deploy`.
4. Run `test_e2e_endpoints.py` (which seeds first — see below).
5. `syndicate clean` again to tear the e2e environment down.

## Running just the tests

```
uv run --project ../backend python test_e2e_endpoints.py              # seed + test
uv run --project ../backend python test_e2e_endpoints.py --skip-seed  # reuse seed data
uv run --project ../backend python test_e2e_endpoints.py --check-creds
```

The orchestrator is fully automatic (mirrors `backend/test_sqs_endpoints.py`):
it validates credentials (syndicate config first, env/SSO fallback), runs
`backend/quick_seed.py` — which writes `ids.json` and `tokens.json` into this
directory because `E2E_ARTIFACTS_DIR` is set — resolves the API Gateway URL
and real DynamoDB table names at runtime, executes every suite in
`e2e.SUITE_ORDER`, prints a colored console summary, and writes
`test_output.pdf`.

## Requirements

- `uv` installed; dependencies come from `backend/pyproject.toml`
  (`uv sync` in `backend/` once).
- Valid AWS credentials: syndicate temp credentials in `syndicate.yml`
  or an active `aws sso login` session.
- A deployed environment (the run scripts deploy one themselves).

#!/usr/bin/env bash
# Full e2e pipeline: syndicate clean -> build -> deploy -> e2e tests -> clean.
#
# While this script runs, syndicate.yml is patched to the dedicated e2e values
# (deploy_target_bucket .../e2e and resources_suffix -dev1) and restored to its
# original content afterwards, no matter how the run ends.
#
# Aborts immediately with an error when AWS credentials are invalid.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
APP_DIR="$BACKEND_DIR/restaurant-backend-app"
CONF_DIR="$APP_DIR/.syndicate-config-dev"
SYNDICATE_YML="$CONF_DIR/syndicate.yml"
BACKUP_FILE="$SYNDICATE_YML.e2e-backup"

E2E_BUCKET="run26-tm3-project-education-artifacts-dev/e2e"
E2E_SUFFIX="-dev1"

export SDCT_CONF="$CONF_DIR"
export PYTHONIOENCODING="utf-8"

red()   { printf '\033[91m%s\033[0m\n' "$*"; }
green() { printf '\033[92m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

if ! command -v uv >/dev/null 2>&1; then
    red "ERROR: 'uv' is required but not installed (https://docs.astral.sh/uv/)."
    exit 1
fi

# ── 1. Validate AWS credentials before touching anything ─────────────────────
bold "==> Checking AWS credentials..."
printf '  \033[2m$ uv run python test_e2e_endpoints.py --check-creds\033[0m\n'
if ! uv run --project "$BACKEND_DIR" python "$SCRIPT_DIR/test_e2e_endpoints.py" --check-creds; then
    red "ERROR: AWS credentials are invalid or expired."
    red "       Refresh the syndicate temp credentials or run 'aws sso login', then retry."
    exit 1
fi

# ── 2. Patch syndicate.yml for the e2e environment (restored on exit) ───────
restore_config() {
    if [ -f "$BACKUP_FILE" ]; then
        mv -f "$BACKUP_FILE" "$SYNDICATE_YML"
        bold "==> Restored original syndicate.yml"
    fi
}
trap restore_config EXIT

bold "==> Patching syndicate.yml (bucket: $E2E_BUCKET, suffix: $E2E_SUFFIX)..."
cp "$SYNDICATE_YML" "$BACKUP_FILE"
sed -e "s|^deploy_target_bucket:.*|deploy_target_bucket: $E2E_BUCKET|" \
    -e "s|^resources_suffix:.*|resources_suffix: $E2E_SUFFIX|" \
    "$SYNDICATE_YML" > "$SYNDICATE_YML.tmp" && mv "$SYNDICATE_YML.tmp" "$SYNDICATE_YML"

syndicate_cmd() {
    printf '  \033[2m$ uv run syndicate %s\033[0m\n' "$*"
    (cd "$APP_DIR" && uv run --project "$BACKEND_DIR" syndicate "$@")
}

# ── 3. syndicate clean / build / deploy ─────────────────────────────────────
bold "==> syndicate clean (pre-run)..."
syndicate_cmd clean || echo "    (nothing to clean — continuing)"

bold "==> syndicate build..."
if ! syndicate_cmd build; then
    red "ERROR: syndicate build failed."
    exit 1
fi

bold "==> syndicate deploy..."
if ! syndicate_cmd deploy; then
    red "ERROR: syndicate deploy failed."
    bold "==> syndicate clean (cleanup after failed deploy)..."
    syndicate_cmd clean || true
    exit 1
fi

# ── 4. Run the e2e tests (seeds first, writes test_output.pdf) ──────────────
bold "==> Running e2e endpoint tests..."
printf '  \033[2m$ uv run python test_e2e_endpoints.py\033[0m\n'
uv run --project "$BACKEND_DIR" python "$SCRIPT_DIR/test_e2e_endpoints.py"
E2E_RC=$?

# ── 5. Tear the e2e environment down again ──────────────────────────────────
bold "==> syndicate clean (post-run)..."
syndicate_cmd clean || red "WARNING: post-run syndicate clean failed — clean up manually."

if [ "$E2E_RC" -eq 0 ]; then
    green "==> E2E run finished: ALL TESTS PASSED (report: $SCRIPT_DIR/test_output.pdf)"
else
    red "==> E2E run finished with failures (report: $SCRIPT_DIR/test_output.pdf)"
fi
exit "$E2E_RC"

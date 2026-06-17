# Full e2e pipeline: syndicate clean -> build -> deploy -> e2e tests -> clean.
#
# While this script runs, syndicate.yml is patched to the dedicated e2e values
# (deploy_target_bucket .../e2e and resources_suffix -dev1) and restored to its
# original content afterwards, no matter how the run ends.
#
# Aborts immediately with an error when AWS credentials are invalid.

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "..\backend" | Resolve-Path | Select-Object -ExpandProperty Path
$AppDir = Join-Path $BackendDir "restaurant-backend-app"
$ConfDir = Join-Path $AppDir ".syndicate-config-dev"
$SyndicateYml = Join-Path $ConfDir "syndicate.yml"
$BackupFile = "$SyndicateYml.e2e-backup"

$E2EBucket = "run26-tm3-project-education-artifacts-dev/e2e"
$E2ESuffix = "-dev1"

$env:SDCT_CONF = $ConfDir
$env:PYTHONIOENCODING = "utf-8"

function Write-Bold($Message) { Write-Host $Message -ForegroundColor White }
function Write-Err($Message) { Write-Host $Message -ForegroundColor Red }
function Write-Ok($Message) { Write-Host $Message -ForegroundColor Green }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Err "ERROR: 'uv' is required but not installed (https://docs.astral.sh/uv/)."
    exit 1
}

function Invoke-Syndicate {
    param([string[]]$SyndicateArgs)
    Push-Location $AppDir
    try {
        Write-Host "  `$ uv run syndicate $($SyndicateArgs -join ' ')" -ForegroundColor DarkGray
        uv run --project $BackendDir syndicate @SyndicateArgs
    }
    finally {
        Pop-Location
    }
}

# -- 1. Validate AWS credentials before touching anything ---------------------
Write-Bold "==> Checking AWS credentials..."
Write-Host "  `$ uv run python test_e2e_endpoints.py --check-creds" -ForegroundColor DarkGray
uv run --project $BackendDir python (Join-Path $ScriptDir "test_e2e_endpoints.py") --check-creds
if ($LASTEXITCODE -ne 0) {
    Write-Err "ERROR: AWS credentials are invalid or expired."
    Write-Err "       Refresh the syndicate temp credentials or run 'aws sso login', then retry."
    exit 1
}

# -- 2. Patch syndicate.yml for the e2e environment (restored in finally) -----
Write-Bold "==> Patching syndicate.yml (bucket: $E2EBucket, suffix: $E2ESuffix)..."
Copy-Item $SyndicateYml $BackupFile -Force

$E2ERc = 1
try {
    $content = Get-Content $SyndicateYml -Raw
    $content = $content -replace "(?m)^deploy_target_bucket:.*$", "deploy_target_bucket: $E2EBucket"
    $content = $content -replace "(?m)^resources_suffix:.*$", "resources_suffix: $E2ESuffix"
    [System.IO.File]::WriteAllText($SyndicateYml, $content, [System.Text.UTF8Encoding]::new($false))

    # -- 3. syndicate clean / build / deploy ----------------------------------
    Write-Bold "==> syndicate clean (pre-run)..."
    Invoke-Syndicate @("clean")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    (nothing to clean - continuing)"
    }

    Write-Bold "==> syndicate build..."
    Invoke-Syndicate @("build")
    if ($LASTEXITCODE -ne 0) {
        Write-Err "ERROR: syndicate build failed."
        exit 1
    }

    Write-Bold "==> syndicate deploy..."
    Invoke-Syndicate @("deploy")
    if ($LASTEXITCODE -ne 0) {
        Write-Err "ERROR: syndicate deploy failed."
        Write-Bold "==> syndicate clean (cleanup after failed deploy)..."
        Invoke-Syndicate @("clean")
        exit 1
    }

    # -- 4. Run the e2e tests (seeds first, writes test_output.pdf) -----------
    Write-Bold "==> Running e2e endpoint tests..."
    Write-Host "  `$ uv run python test_e2e_endpoints.py" -ForegroundColor DarkGray
    uv run --project $BackendDir python (Join-Path $ScriptDir "test_e2e_endpoints.py")
    $E2ERc = $LASTEXITCODE

    # -- 5. Tear the e2e environment down again --------------------------------
    Write-Bold "==> syndicate clean (post-run)..."
    Invoke-Syndicate @("clean")
    if ($LASTEXITCODE -ne 0) {
        Write-Err "WARNING: post-run syndicate clean failed - clean up manually."
    }
}
finally {
    if (Test-Path $BackupFile) {
        Move-Item $BackupFile $SyndicateYml -Force
        Write-Bold "==> Restored original syndicate.yml"
    }
}

if ($E2ERc -eq 0) {
    Write-Ok "==> E2E run finished: ALL TESTS PASSED (report: $ScriptDir\test_output.pdf)"
} else {
    Write-Err "==> E2E run finished with failures (report: $ScriptDir\test_output.pdf)"
}
exit $E2ERc

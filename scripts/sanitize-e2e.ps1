[CmdletBinding()]
param(
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path "model\.env")) {
    throw "model\.env is required. Copy model\.env.example to model\.env and set ML_SERVICE_TOKEN."
}

function Get-EnvValue([string]$path, [string]$name) {
    $line = Get-Content $path | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    if ($null -eq $line) {
        return ""
    }
    return $line.Substring($name.Length + 1)
}

$backendToken = Get-EnvValue "backend\.env" "ML_SERVICE_TOKEN"
$modelToken = Get-EnvValue "model\.env" "ML_SERVICE_TOKEN"
if ([string]::IsNullOrWhiteSpace($backendToken) -or $backendToken -eq "replace-with-a-random-shared-secret") {
    throw "backend\.env must define a non-placeholder ML_SERVICE_TOKEN."
}
if ([string]::IsNullOrWhiteSpace($modelToken) -or $modelToken -eq "replace-with-the-same-random-secret-used-by-django") {
    throw "model\.env must define the same non-placeholder ML_SERVICE_TOKEN as backend\.env."
}
if ($backendToken -cne $modelToken) {
    throw "backend\.env and model\.env must use the same ML_SERVICE_TOKEN."
}

$composeArgs = @("compose")
if ($NoBuild) {
    $composeArgs += @("up", "-d", "postgres", "redis", "ml_service", "backend")
} else {
    $composeArgs += @("up", "-d", "--build", "postgres", "redis", "ml_service", "backend")
}

& docker @composeArgs
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start the Request Shield dependencies."
}

try {
    & docker compose exec -T backend python manage.py migrate --check
    if ($LASTEXITCODE -ne 0) {
        throw "Django migrations are not up to date."
    }

    & docker compose exec -T backend python manage.py check
    if ($LASTEXITCODE -ne 0) {
        throw "Django system checks failed."
    }

    & docker compose exec -T backend python manage.py sanitize_e2e
    if ($LASTEXITCODE -ne 0) {
        throw "Request Shield Docker E2E test failed."
    }
} finally {
    & docker compose logs --tail 100 backend ml_service
}

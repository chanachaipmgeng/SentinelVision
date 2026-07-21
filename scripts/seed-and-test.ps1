# Seed demo data + run API smoke tests (requires docker compose stack up)
param(
  [switch]$Reset
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Ensure DB is healthy"
docker compose ps db

$seedArgs = @("scripts/seed_demo_data.py")
if ($Reset) { $seedArgs += "--reset" }

Write-Host "==> Seed demo data (mount local API-Fast)"
docker compose run --rm `
  -v "${root}/API-Fast:/app" `
  --entrypoint python `
  api @seedArgs

Write-Host "==> Smoke test API via compose network (http://api:8000)"
docker compose run --rm `
  -v "${root}/API-Fast:/app" `
  --entrypoint python `
  api scripts/smoke_test_api.py --base-url http://api:8000

Write-Host ""
Write-Host "Accounts: sysadmin / admin / boss / emp1 / emp2"
Write-Host "Password: Password123!"

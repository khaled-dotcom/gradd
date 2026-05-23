# Start Airflow for EmpowerWork jobs pipeline (every 8 hours).
# Requires: Docker Desktop, .env with DB_* for Azure MySQL
# Run from repo root: .\scripts\azure-airflow-start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env missing. Copy from azure-deploy-output.env and set DB_HOST, DB_USER, DB_PASS, DB_NAME" -ForegroundColor Red
    exit 1
}

Write-Host "=== Airflow (jobs pipeline every 8h) ===" -ForegroundColor Cyan

# MySQL firewall for this machine (pipeline LOAD stage)
try {
    $ip = (Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 10).ip
    $rule = "airflow-$($ip.Replace('.','-'))"
    az mysql flexible-server firewall-rule create -g rg-empowerwork -n ewsw55166db `
        --rule-name $rule --start-ip-address $ip --end-ip-address $ip -o none 2>$null
    Write-Host "  MySQL firewall: $ip" -ForegroundColor DarkGray
} catch {
    Write-Host "  WARN: Could not add MySQL firewall rule" -ForegroundColor Yellow
}

$env:AIRFLOW_UID = "50000"
docker compose -f data-engineering/docker-compose.data.yml up -d

Write-Host ""
Write-Host "Airflow UI: http://localhost:8085  (admin / admin)" -ForegroundColor Green
Write-Host "DAG: empowerwork_software_jobs_pipeline" -ForegroundColor Green
Write-Host "1. Open UI -> DAGs -> toggle ON (unpause)" -ForegroundColor Yellow
Write-Host "2. Schedule: every 8 hours (0 */8 * * *)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Manual run (no Airflow):" -ForegroundColor Cyan
Write-Host "  python data-engineering/pipeline/run.py"
Write-Host ""
Write-Host "Admin manual trigger (website):" -ForegroundColor Cyan
Write-Host "  Admin -> Jobs -> Run import now (requires admin login)"

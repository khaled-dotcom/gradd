# Run daily analytics with Apache Spark (PySpark local[*] on Windows)
# From project root:  .\scripts\run-spark-analytics.ps1
#
# Requires Java 11+ (Spark downloads its own runtime deps via pip).
# Alternative without local Java: use Docker Spark job:
#   docker compose -f docker-compose.events.yml run --rm spark-analytics

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing PySpark if needed..." -ForegroundColor Cyan
python -m pip install -q pyspark

$env:USE_SPARK = "true"
if (-not $env:SPARK_MASTER) {
    $env:SPARK_MASTER = "local[*]"
}

Write-Host "Running Spark analytics (master=$env:SPARK_MASTER)..." -ForegroundColor Cyan
python backend/spark_jobs/analytics_daily.py

if (Test-Path "data/reports/latest.json") {
    $r = Get-Content "data/reports/latest.json" -Raw | ConvertFrom-Json
    Write-Host "Report engine: $($r.engine) | total_events: $($r.total_events)" -ForegroundColor Green
}

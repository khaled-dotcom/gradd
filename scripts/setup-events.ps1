# One-time setup for Kafka/Spark demo on Windows (PowerShell)
# Run from project root:  .\scripts\setup-events.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing Python dependencies (api/requirements.txt)..." -ForegroundColor Cyan
python -m pip install -r api/requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
} else {
    Write-Host ".env already exists (not overwritten)" -ForegroundColor Yellow
}

if (-not (Test-Path "frontend\.env")) {
    Copy-Item "frontend\.env.example" "frontend\.env"
    Write-Host "Created frontend/.env from frontend/.env.example" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start Docker Desktop, then:"
Write-Host "     docker compose -f docker-compose.events.yml up -d"
Write-Host "  2. Backend:"
Write-Host "     uvicorn backend.src.main:app --reload --port 8000"
Write-Host "  3. Workers (new terminal):"
Write-Host "     python scripts/run_workers.py"
Write-Host "  4. Frontend:"
Write-Host "     cd frontend; npm run dev"
Write-Host "  5. Spark analytics (after events in data/lake):"
Write-Host "     .\scripts\run-spark-analytics.ps1"
Write-Host "     # or: docker compose -f docker-compose.events.yml run --rm spark-analytics"

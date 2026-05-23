# Seed Azure / remote MySQL — set DB_* in .env first (see .env.azure.example)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Creating base tables (SQLAlchemy)..." -ForegroundColor Cyan
python -c "from backend.src.db.database import engine, Base; import backend.src.db.models  # noqa: F401; Base.metadata.create_all(bind=engine); print('Tables OK')"

Write-Host "Running migrations..." -ForegroundColor Cyan
python backend/scripts/migrations/migrate_disabilities.py
python backend/scripts/migrations/migrate_tools.py
python backend/scripts/migrations/migrate_jobs_created_at.py
python backend/scripts/migrations/migrate_applications_table.py
python backend/scripts/migrations/fix_all_database_issues.py

Write-Host "Seeding data..." -ForegroundColor Cyan
$env:PYTHONPATH = "$Root;$(Join-Path $Root 'backend')"
Push-Location (Join-Path $Root "backend")
python scripts/seeds/seed_disabilities.py
python scripts/seeds/seed_assistive_tools.py
python scripts/seeds/seed_jobs.py
Pop-Location

Write-Host "Create admin (edit email/password below if needed):" -ForegroundColor Cyan
python backend/scripts/create_admin_user.py admin@test.com Admin123456!

Write-Host "Optional Chroma reindex (needs OPENAI_API_KEY):" -ForegroundColor Yellow
Write-Host "  python backend/scripts/reindex_chroma.py"

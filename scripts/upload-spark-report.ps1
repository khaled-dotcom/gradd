# Upload data/reports/latest.json to Azure Blob (after local Spark job)
# Requires AZURE_STORAGE_CONNECTION_STRING in .env or environment

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$report = Join-Path $Root "data\reports\latest.json"
if (-not (Test-Path $report)) {
    Write-Host "Run Spark first: docker compose -f docker-compose.events.yml run --rm spark-analytics" -ForegroundColor Red
    exit 1
}

python -c @"
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from backend.src.config import settings
from backend.src.utils.blob_storage import upload_spark_report, blob_enabled

if not blob_enabled():
    raise SystemExit('Set AZURE_STORAGE_CONNECTION_STRING in .env')

ok = upload_spark_report(Path('data/reports/latest.json'), settings.AZURE_SPARK_REPORT_BLOB)
print('Uploaded to blob:', settings.AZURE_SPARK_REPORT_BLOB if ok else 'failed')
"@

"""Spark analytics report API (admin)."""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.src.config import settings
from backend.src.utils.blob_storage import blob_enabled, download_blob

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])


def _load_report() -> dict:
    if blob_enabled():
        data = download_blob(settings.AZURE_SPARK_REPORT_BLOB)
        if data:
            return json.loads(data.decode("utf-8"))

    path = Path(settings.SPARK_REPORT_PATH)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


@router.get("/spark")
def get_spark_analytics():
    """Return latest batch analytics report (local file or Azure Blob)."""
    report = _load_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No analytics report yet. Run: python backend/spark_jobs/analytics_daily.py "
                "or scripts/upload-spark-report.ps1"
            ),
        )
    return report

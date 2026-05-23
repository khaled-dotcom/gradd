"""Spark: quality metrics on Gold layer -> JSON report."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-engineering"))
from spark_jobs.common import lake_root  # noqa: E402


def main():
    spark = SparkSession.builder.appName("jobs_quality_metrics").getOrCreate()
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gold_path = lake_root() / "gold" / dt
    report_path = ROOT / "data" / "reports" / "jobs_quality.json"

    if not gold_path.exists():
        report = {"dt": dt, "status": "no_data", "total": 0}
    else:
        df = spark.read.parquet(str(gold_path))
        total = df.count()
        by_source = df.groupBy("source").count().collect()
        accessible = df.filter(df.is_accessible_focus == True).count()  # noqa: E712
        null_title = df.filter(df.title.isNull() | (df.title == "")).count()
        report = {
            "dt": dt,
            "status": "ok",
            "total": total,
            "accessible_count": accessible,
            "null_title": null_title,
            "by_source": {r.source: r["count"] for r in by_source},
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Quality report: {report_path}")
    spark.stop()


if __name__ == "__main__":
    main()

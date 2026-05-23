"""
Daily analytics batch job (Apache Spark via PySpark, or pandas fallback).

Run with Spark (recommended for thesis):
  $env:USE_SPARK = "true"
  python backend/spark_jobs/analytics_daily.py

Or via Docker (no local Java/PySpark needed):
  docker compose -f docker-compose.events.yml run --rm spark-analytics
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class _Settings:
    """Env-only settings so spark-submit in Docker needs no pip extras."""

    ANALYTICS_DATA_PATH = os.getenv("ANALYTICS_DATA_PATH", "./data/lake")
    SPARK_REPORT_PATH = os.getenv("SPARK_REPORT_PATH", "./data/reports/latest.json")
    SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
    USE_SPARK = os.getenv("USE_SPARK", "true").lower() in ("1", "true", "yes")


settings = _Settings()


def _load_events_pandas(lake: Path) -> list[dict]:
    rows = []
    if not lake.exists():
        return rows
    for dt_dir in lake.glob("dt=*"):
        for f in dt_dir.glob("*.jsonl"):
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
    return rows


def _aggregate_from_records(records: list) -> dict:
    if not records:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_events": 0,
            "by_event_type": {},
            "chat_events_total": 0,
            "application_events_total": 0,
            "top_jobs_applied": [],
        }
    types = Counter(r.get("event_type") for r in records)
    job_apps = Counter()
    for r in records:
        if r.get("event_type") in ("ApplicationSubmitted", "CvParsed"):
            jid = (r.get("payload") or {}).get("job_id")
            if jid:
                job_apps[jid] += 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_events": len(records),
        "by_event_type": dict(types),
        "chat_events_total": sum(c for t, c in types.items() if str(t).startswith("Chat")),
        "application_events_total": sum(
            c for t, c in types.items() if "Application" in str(t) or "Cv" in str(t)
        ),
        "top_jobs_applied": [{"job_id": k, "count": v} for k, v in job_apps.most_common(10)],
    }


def _aggregate_spark(lake: Path) -> dict:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.master(settings.SPARK_MASTER)
        .appName("EmpowerWorkAnalytics")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    try:
        paths = [str(p) for p in lake.glob("dt=*/*.jsonl")]
        if not paths:
            base = _aggregate_from_records([])
            base["engine"] = "pyspark"
            return base

        df = spark.read.json(paths)
        total = df.count()
        by_type_rows = df.groupBy("event_type").count().collect()
        by_event_type = {r["event_type"]: r["count"] for r in by_type_rows if r["event_type"]}

        chat_events_total = df.filter(F.col("event_type").startswith("Chat")).count()
        application_events_total = df.filter(
            F.col("event_type").contains("Application") | F.col("event_type").contains("Cv")
        ).count()

        top_jobs = (
            df.filter(F.col("event_type").isin("ApplicationSubmitted", "CvParsed"))
            .select(F.col("payload.job_id").alias("job_id"))
            .filter(F.col("job_id").isNotNull())
            .groupBy("job_id")
            .count()
            .orderBy(F.desc("count"))
            .limit(10)
            .collect()
        )
        top_jobs_applied = [{"job_id": r["job_id"], "count": r["count"]} for r in top_jobs]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_events": total,
            "by_event_type": by_event_type,
            "chat_events_total": chat_events_total,
            "application_events_total": application_events_total,
            "top_jobs_applied": top_jobs_applied,
            "engine": "pyspark",
            "spark_master": settings.SPARK_MASTER,
        }
    finally:
        spark.stop()


def main():
    lake = Path(settings.ANALYTICS_DATA_PATH)
    report_path = Path(settings.SPARK_REPORT_PATH)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    use_spark = os.getenv("USE_SPARK", settings.USE_SPARK).lower()
    report = None

    if use_spark in ("1", "true", "yes", "auto"):
        try:
            report = _aggregate_spark(lake)
            print(f"Spark report ({settings.SPARK_MASTER})")
        except Exception as e:
            print(f"Spark unavailable, using pandas: {e}")

    if report is None:
        records = _load_events_pandas(lake) if lake.exists() else []
        report = _aggregate_from_records(records)
        report["engine"] = "pandas"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote report to {report_path} (engine={report.get('engine')})")


if __name__ == "__main__":
    main()

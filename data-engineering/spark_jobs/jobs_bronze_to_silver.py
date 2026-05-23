"""
Spark: Bronze JSONL -> Silver Parquet (cleansed, typed).
  spark-submit data-engineering/spark_jobs/jobs_bronze_to_silver.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-engineering"))
from spark_jobs.common import bronze_to_draft, lake_root  # noqa: E402


def main():
    spark = SparkSession.builder.appName("jobs_bronze_to_silver").getOrCreate()
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bronze_glob = str(lake_root() / "bronze" / "source=*" / f"dt={dt}" / "*.jsonl")
    silver_path = lake_root() / "silver" / dt

    rows = []
    for path in Path(lake_root() / "bronze").rglob("*.jsonl"):
        if f"dt={dt}" not in str(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                draft = bronze_to_draft(row)
                if draft.get("external_id"):
                    rows.append(draft)

    if not rows:
        print("No bronze rows for today — skipping silver write")
        spark.stop()
        return

    schema = StructType(
        [
            StructField("source", StringType()),
            StructField("external_id", StringType()),
            StructField("source_url", StringType()),
            StructField("title", StringType()),
            StructField("description", StringType()),
            StructField("company_name", StringType()),
            StructField("city", StringType()),
            StructField("country", StringType()),
            StructField("employment_type", StringType()),
            StructField("remote_type", StringType()),
            StructField("requirements", StringType()),
            StructField("content_hash", StringType()),
            StructField("is_accessible_focus", StringType()),
            StructField("disability_tags", StringType()),
            StructField("fetched_at", StringType()),
        ]
    )
    flat = []
    for r in rows:
        flat.append(
            {
                **{k: r[k] for k in r if k not in ("requirements", "disability_tags")},
                "requirements": json.dumps(r.get("requirements") or []),
                "disability_tags": json.dumps(r.get("disability_tags") or []),
            }
        )
    df = spark.createDataFrame(flat, schema=schema)
    df = df.withColumn("is_accessible_focus", F.col("is_accessible_focus").cast("boolean"))
    silver_path.mkdir(parents=True, exist_ok=True)
    df.write.mode("overwrite").parquet(str(silver_path))
    print(f"Silver written: {silver_path} ({df.count()} rows)")
    spark.stop()


if __name__ == "__main__":
    main()

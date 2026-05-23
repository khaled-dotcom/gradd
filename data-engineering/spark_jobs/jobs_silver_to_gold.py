"""
Spark: Silver -> Gold (dedup, Egypt filter, dimensional keys).
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-engineering"))
from spark_jobs.common import egypt_match, lake_root, software_match  # noqa: E402


def main():
    spark = SparkSession.builder.appName("jobs_silver_to_gold").getOrCreate()
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    silver_path = lake_root() / "silver" / dt
    gold_path = lake_root() / "gold" / dt

    if not silver_path.exists():
        print(f"No silver at {silver_path}")
        spark.stop()
        return

    df = spark.read.parquet(str(silver_path))

    # Egypt filter (UDF-like with filter)
    def keep_row(row):
        text = f"{row.title} {row.description}"
        if not egypt_match(row.country or "", row.city or "", text):
            return False
        return software_match(row.title or "", row.description or "")

    collected = df.collect()
    kept = [r.asDict() for r in collected if keep_row(r)]
    if not kept:
        print("No Egypt rows after filter")
        spark.stop()
        return

    gold_df = spark.createDataFrame(kept)
    w = Window.partitionBy("source", "external_id").orderBy(F.col("fetched_at").desc())
    gold_df = gold_df.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") == 1).drop("rn")
    gold_df = gold_df.withColumn("is_active", F.lit(True))
    gold_df = gold_df.withColumn("last_seen_at", F.current_timestamp())

    gold_path.mkdir(parents=True, exist_ok=True)
    gold_df.write.mode("overwrite").parquet(str(gold_path))
    print(f"Gold written: {gold_path} ({gold_df.count()} rows)")
    spark.stop()


if __name__ == "__main__":
    main()

"""
Stage 2 — TRANSFORM (Silver → Gold)
Clean, hash, Egypt filter, software filter, dedupe → Parquet
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_transform(repo_root: Path, de_root: Path, use_spark: bool = False) -> bool:
    print("=" * 60)
    print("STAGE 2: TRANSFORM → Silver + Gold (Parquet)")
    print("=" * 60)

    if use_spark or __import__("os").environ.get("USE_SPARK", "").lower() in ("1", "true"):
        try:
            for script in (
                "jobs_bronze_to_silver.py",
                "jobs_silver_to_gold.py",
                "jobs_quality_metrics.py",
            ):
                print(f"  Spark: {script}")
                subprocess.run(
                    [sys.executable, str(de_root / "spark_jobs" / script)],
                    cwd=str(repo_root),
                    check=True,
                )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"  Spark failed ({exc}), falling back to Pandas")

    script = de_root / "scripts" / "medallion_pandas.py"
    subprocess.run([sys.executable, str(script)], cwd=str(repo_root), check=True)
    return True

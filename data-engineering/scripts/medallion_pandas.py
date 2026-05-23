"""Pandas fallback when PySpark is not installed (dev/Windows)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DE = ROOT / "data-engineering"
sys.path.insert(0, str(DE))
from spark_jobs.common import bronze_to_draft, egypt_match, lake_root, software_match  # noqa: E402


def bronze_to_silver():
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for path in (lake_root() / "bronze").rglob("*.jsonl"):
        if f"dt={dt}" not in str(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(bronze_to_draft(json.loads(line)))
    if not rows:
        print("No bronze rows")
        return
    df = pd.DataFrame(rows)
    out_dir = lake_root() / "silver" / dt
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "jobs.parquet", index=False)
    print(f"Silver (pandas): {out_dir} ({len(df)} rows)")


def silver_to_gold():
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    silver = lake_root() / "silver" / dt
    if not silver.exists():
        print("No silver")
        return
    pq = silver / "jobs.parquet"
    df = pd.read_parquet(pq if pq.exists() else silver)
    def _keep(r):
        title = str(r.get("title", ""))
        desc = str(r.get("description", ""))
        if not egypt_match(str(r.get("country", "")), str(r.get("city", "")), f"{title} {desc}"):
            return False
        return software_match(title, desc)

    df = df[df.apply(_keep, axis=1)]
    df = df.sort_values("fetched_at", ascending=False).drop_duplicates(
        subset=["source", "external_id"], keep="first"
    )
    df["is_active"] = True
    df["last_seen_at"] = datetime.now(timezone.utc).isoformat()
    out_dir = lake_root() / "gold" / dt
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "jobs.parquet", index=False)
    print(f"Gold (pandas): {out_dir} ({len(df)} rows)")


if __name__ == "__main__":
    bronze_to_silver()
    silver_to_gold()

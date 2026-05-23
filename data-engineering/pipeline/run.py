#!/usr/bin/env python3
"""
EmpowerWork jobs pipeline — entry point.

  python data-engineering/pipeline/run.py

Stages:
  1. extract  — scrape Wuzzuf + Forasna + LinkedIn (software/IT, Egypt)
  2. transform — Bronze → Silver → Gold (filters + dedupe)
  3. load     — Gold Parquet → MySQL

Schedule: every 8 hours (Airflow DAG or cron — see config/pipeline.yaml)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DE = REPO / "data-engineering"

sys.path.insert(0, str(DE))
sys.path.insert(0, str(REPO))

from pipeline.stages.extract import run_extract  # noqa: E402
from pipeline.stages.transform import run_transform  # noqa: E402
from pipeline.stages.load import run_load  # noqa: E402


def main() -> int:
    print("\nEmpowerWork Jobs Pipeline")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}\n")

    run_extract(REPO, DE)
    run_transform(REPO, DE)
    result = run_load(REPO)

    if result.get("status") == "db_unavailable":
        print("\nWARN: MySQL unreachable — run scripts/azure-start.ps1")
        return 0

    print(f"\nFinished: {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

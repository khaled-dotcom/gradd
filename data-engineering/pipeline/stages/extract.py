"""
Stage 1 — EXTRACT (Bronze)
Scrape Wuzzuf, Forasna, LinkedIn → JSONL in data/lake/jobs/bronze/
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from connectors import CONNECTORS


def run_extract(repo_root: Path, de_root: Path) -> Dict[str, int]:
    cfg_path = de_root / "config" / "sources.yaml"
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    lake = repo_root / "data" / "lake" / "jobs"
    counts: Dict[str, int] = {}

    print("=" * 60)
    print("STAGE 1: EXTRACT → Bronze (live scrape, software/IT only)")
    print("=" * 60)

    for name, cls in CONNECTORS.items():
        src_cfg = cfg.get("sources", {}).get(name, {})
        if not src_cfg.get("enabled", False):
            print(f"  [{name}] skipped (disabled in sources.yaml)")
            continue
        display = src_cfg.get("display_name", name)
        print(f"\n  [{name}] {display} — fetching up to {src_cfg.get('max_jobs_per_run')} jobs...")
        conn = cls(
            lake,
            max_jobs=src_cfg.get("max_jobs_per_run", 30),
            config=src_cfg,
        )
        records = conn.fetch()
        path = conn.write_bronze(records)
        counts[name] = len(records)
        print(f"  [{name}] wrote {len(records)} rows → {path}")

    print(f"\nExtract totals: {counts}")
    return counts

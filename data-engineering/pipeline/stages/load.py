"""
Stage 3 — LOAD (Gold → MySQL)
Upsert jobs into production DB + import_runs audit
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict


def run_load(repo_root: Path) -> Dict[str, Any]:
    print("=" * 60)
    print("STAGE 3: LOAD → MySQL (EmpowerWork app)")
    print("=" * 60)

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.src.services.job_warehouse_loader import load_gold_to_mysql

    result = load_gold_to_mysql()
    print(f"  Result: {result}")
    return result

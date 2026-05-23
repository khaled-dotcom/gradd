#!/usr/bin/env python3
"""Backward-compatible wrapper — use pipeline/run.py for the staged pipeline."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
runner = ROOT / "data-engineering" / "pipeline" / "run.py"
sys.exit(subprocess.call([sys.executable, str(runner)], cwd=str(ROOT)))

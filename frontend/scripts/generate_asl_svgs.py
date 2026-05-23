"""
Legacy entry point — regenerates the full A–Z ASL fingerspell set.

Preferred pipeline:
  1. python scripts/extract_asl_from_banner.py      (11 letters from NTI banner)
  2. python scripts/extract_asl_from_wikimedia.py   (15 letters, detailed line art)

Requires: pip install pillow; network for step 2 (first run).
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    py = sys.executable
    for name in ("extract_asl_from_banner.py", "extract_asl_from_wikimedia.py"):
        script = SCRIPT_DIR / name
        print(f"Running {name}...")
        subprocess.run([py, str(script)], check=True)
    print("All ASL glyphs regenerated.")


if __name__ == "__main__":
    main()

"""
Start all Kafka workers in separate processes (thesis demo).

  python scripts/run_workers.py

Requires: EVENTS_ENABLED=true, docker compose -f docker-compose.events.yml up -d
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKERS = [
    "backend.workers.cv_worker",
    "backend.workers.chat_worker",
    "backend.workers.job_embedding_worker",
    "backend.workers.analytics_sink",
]

if __name__ == "__main__":
    procs = []
    for mod in WORKERS:
        print(f"Starting {mod}...")
        p = subprocess.Popen([sys.executable, "-m", mod], cwd=str(ROOT))
        procs.append(p)
    print("Workers running. Ctrl+C to stop.")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()

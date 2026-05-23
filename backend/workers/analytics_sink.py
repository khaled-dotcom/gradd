"""Fan-in all domain events to Parquet files for Spark batch jobs."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.src.config import settings
from backend.src.events.schemas import EventEnvelope, Topics
from backend.workers.base import run_consumer

logger = logging.getLogger(__name__)


def _lake_path() -> Path:
    root = Path(settings.ANALYTICS_DATA_PATH)
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return root / f"dt={dt}"


def handle_event(event: EventEnvelope) -> None:
    out_dir = _lake_path()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{event.event_id}.jsonl"
    record = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "user_id": event.user_id,
        "payload": event.payload,
    }
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    run_consumer(
        [Topics.APPLICATION, Topics.JOB, Topics.CHAT],
        "analytics-sink",
        handle_event,
    )

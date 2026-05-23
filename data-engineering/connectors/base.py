"""Base connector — writes Bronze JSONL records."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BronzeRecord:
    source: str
    external_id: str
    source_url: str
    fetched_at: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobDraft:
    """Silver/Gold unified job shape."""
    source: str
    external_id: str
    source_url: str
    title: str
    description: str
    company_name: str
    city: str
    country: str
    employment_type: str
    remote_type: str
    requirements: List[str]
    content_hash: str
    is_accessible_focus: bool
    disability_tags: List[str]
    fetched_at: str


class BaseConnector(ABC):
    source_name: str = "base"

    def __init__(
        self,
        lake_root: Path,
        max_jobs: int = 50,
        config: Optional[dict] = None,
    ):
        self.lake_root = lake_root
        self.max_jobs = max_jobs
        self.config = config or {}

    def bronze_path(self, dt: Optional[str] = None) -> Path:
        dt = dt or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (
            self.lake_root
            / "bronze"
            / f"source={self.source_name}"
            / f"dt={dt}"
        )

    def write_bronze(self, records: List[BronzeRecord], dt: Optional[str] = None) -> Path:
        out_dir = self.bronze_path(dt)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"batch_{datetime.now(timezone.utc).strftime('%H%M%S')}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return out_file

    @abstractmethod
    def fetch(self) -> List[BronzeRecord]:
        ...

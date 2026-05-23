"""Shared helpers for PySpark job scripts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def lake_root() -> Path:
    cfg = load_yaml("pipeline.yaml")
    return REPO_ROOT / cfg.get("lake_root", "data/lake/jobs")


def content_hash(title: str, description: str, company: str) -> str:
    blob = f"{title}|{description}|{company}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def egypt_match(country: str, city: str, text: str) -> bool:
    cfg = load_yaml("egypt_filters.yaml")
    hay = f"{country} {city} {text}".lower()
    for c in cfg.get("country_names", []):
        if c.lower() in hay:
            return True
    for city_name in cfg.get("cities", []):
        if city_name.lower() in hay:
            return True
    return False


def software_match(title: str, description: str) -> bool:
    """True if job looks like software/IT (see config/software_filters.yaml)."""
    cfg = load_yaml("software_filters.yaml")
    if not cfg.get("enabled", True):
        return True
    hay = f"{title} {description}".lower()
    for ex in cfg.get("exclude_keywords", []):
        if ex.lower() in hay:
            return False
    for kw in cfg.get("title_keywords", []):
        if kw.lower() in hay:
            return True
    return False


def accessible_flags(text: str) -> tuple[bool, List[str]]:
    cfg = load_yaml("egypt_filters.yaml")
    hay = (text or "").lower()
    tags = []
    for kw in cfg.get("accessible_keywords", []):
        if kw.lower() in hay:
            tags.append(kw)
    return bool(tags), tags


def bronze_to_draft(raw_row: Dict[str, Any]) -> Dict[str, Any]:
    """Map bronze JSONL row to silver fields."""
    raw = raw_row.get("raw") or raw_row
    if isinstance(raw, str):
        raw = json.loads(raw)
    title = strip_html(str(raw.get("title", "Untitled")))
    description = strip_html(str(raw.get("description", "")))
    company = str(raw.get("company", raw.get("company_name", "Unknown")))
    city = str(raw.get("city", "Cairo"))
    country = str(raw.get("country", "Egypt"))
    emp = str(raw.get("employment_type", "full-time"))
    remote = str(raw.get("remote_type", "remote"))
    reqs = raw.get("requirements") or []
    if isinstance(reqs, str):
        reqs = [reqs]
    text = f"{title} {description}"
    is_acc, _ = accessible_flags(text)
    is_sw = software_match(title, description)
    return {
        "source": raw_row.get("source", "unknown"),
        "external_id": str(raw_row.get("external_id", "")),
        "source_url": str(raw_row.get("source_url", "")),
        "title": title[:255],
        "description": description[:5000],
        "company_name": company[:255],
        "city": city[:100],
        "country": country[:100],
        "employment_type": emp if emp in ("full-time", "part-time", "contract", "internship") else "full-time",
        "remote_type": remote if remote in ("remote", "on-site", "hybrid") else "remote",
        "requirements": [str(r)[:500] for r in reqs[:20]],
        "content_hash": content_hash(title, description, company),
        "is_accessible_focus": is_acc,
        "is_software_focus": is_sw,
        "disability_tags": accessible_flags(text)[1],
        "fetched_at": raw_row.get("fetched_at", ""),
    }

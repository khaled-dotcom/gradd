"""Shared HTML scraping helpers for Egypt job board connectors."""
from __future__ import annotations

import json
import re
import time
from html import unescape
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

USER_AGENT = "EmpowerWork/1.0 (+job-aggregator; contact=admin@empowerwork.local)"
REQUEST_TIMEOUT = 25
REQUEST_DELAY_SEC = 0.5


def load_software_config() -> dict:
    path = CONFIG_DIR / "software_filters.yaml"
    if not path.exists():
        return {"enabled": True, "title_keywords": ["software", "developer"]}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def software_match(title: str, description: str) -> bool:
    cfg = load_software_config()
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


def fetch_html(url: str, session: Optional[requests.Session] = None) -> str:
    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", USER_AGENT)
    sess.headers.setdefault("Accept-Language", "en-US,en;q=0.9,ar;q=0.8")
    resp = sess.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    time.sleep(REQUEST_DELAY_SEC)
    return resp.text


def parse_job_posting_ld(html: str) -> Optional[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "null")
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def parse_og_meta(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    out: Dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if key and content:
            out[key] = content.strip()
    return out


def strip_tags(text: str) -> str:
    if not text:
        return ""
    if "<" in text and ">" in text:
        return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return unescape(text).strip()


def location_from_ld(job: Dict[str, Any]) -> tuple[str, str]:
    country, city = "Egypt", ""
    loc = job.get("jobLocation")
    if isinstance(loc, dict):
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            country = str(addr.get("addressCountry") or country)
            city = str(addr.get("addressLocality") or addr.get("addressRegion") or "")
    return country[:100], city[:100]


def company_from_ld(job: Dict[str, Any]) -> str:
    org = job.get("hiringOrganization") or {}
    if isinstance(org, dict):
        return str(org.get("name") or "Unknown")[:255]
    return str(org)[:255] if org else "Unknown"


def parse_wuzzuf_og_title(og_title: str) -> tuple[str, str, str]:
    """'HR Specialist job at Takatof Foundation in New Cairo, Cairo – Apply on Wuzzuf'"""
    title, company, city = "Untitled", "Unknown", "Cairo"
    if not og_title:
        return title, company, city
    m = re.match(
        r"^(.+?)\s+job at\s+(.+?)\s+in\s+(.+?)\s*(?:[–\-|]|Apply)",
        og_title,
        re.I,
    )
    if m:
        title, company, city = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    else:
        title = og_title.split("–")[0].split("-")[0].strip() or title
    return title[:255], company[:255], city[:100]


def wuzzuf_external_id(job_path: str) -> str:
    """/jobs/p/ps7iscd8c8h0-slug... -> ps7iscd8c8h0"""
    path = job_path.split("?")[0].rstrip("/")
    parts = path.split("/")
    if "jobs" in parts and "p" in parts:
        idx = parts.index("p") + 1
        if idx < len(parts):
            slug = parts[idx]
            return slug.split("-")[0] if slug else slug
    return path


def forasna_external_id(job_url: str) -> str:
    path = urlparse(job_url).path.rstrip("/")
    tail = path.split("/")[-1]
    m = re.search(r"-(\d+)$", tail)
    if m:
        return m.group(1)
    if len(tail) > 64:
        import hashlib

        return hashlib.sha256(tail.encode()).hexdigest()[:16]
    return tail[:64]


def employment_from_text(text: str) -> str:
    t = (text or "").lower()
    if "part-time" in t or "part time" in t:
        return "part-time"
    if "intern" in t:
        return "internship"
    if "contract" in t or "freelance" in t:
        return "contract"
    return "full-time"


def remote_from_text(text: str) -> str:
    t = (text or "").lower()
    if "remote" in t or "work from home" in t or "من المنزل" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return "on-site"


def collect_links(html: str, pattern: str, base_url: str) -> List[str]:
    found = re.findall(pattern, html)
    out: List[str] = []
    seen = set()
    for href in found:
        full = urljoin(base_url, href)
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out

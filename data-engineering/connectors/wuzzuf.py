"""Wuzzuf connector — live scrape Egypt software/IT listings."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from urllib.parse import quote_plus

import requests

from .base import BaseConnector, BronzeRecord
from .scrape_common import (
    collect_links,
    company_from_ld,
    employment_from_text,
    fetch_html,
    load_software_config,
    location_from_ld,
    parse_job_posting_ld,
    parse_og_meta,
    parse_wuzzuf_og_title,
    remote_from_text,
    software_match,
    strip_tags,
    wuzzuf_external_id,
)

WUZZUF_SEARCH = "https://wuzzuf.net/search/jobs/?q={query}&l=egypt&start={start}"
JOB_LINK_RE = r'href="(/jobs/p/[^"]+)"'


class WuzzufConnector(BaseConnector):
    source_name = "wuzzuf"

    def __init__(self, lake_root, max_jobs: int = 50, config: dict | None = None):
        super().__init__(lake_root, max_jobs, config)
        self.list_pages = int(self.config.get("list_pages", 4))
        self.page_size = int(self.config.get("page_size", 15))
        sw = load_software_config()
        self.search_queries: List[str] = sw.get("search_queries", {}).get(
            "wuzzuf",
            ["software", "python developer", "frontend developer"],
        )

    def _collect_job_paths(self, session: requests.Session) -> List[str]:
        paths: List[str] = []
        seen = set()
        for query in self.search_queries:
            if len(paths) >= self.max_jobs:
                break
            for page in range(self.list_pages):
                if len(paths) >= self.max_jobs:
                    break
                start = page * self.page_size
                list_url = WUZZUF_SEARCH.format(query=quote_plus(query), start=start)
                try:
                    html = fetch_html(list_url, session)
                except Exception as exc:
                    print(f"  wuzzuf list q={query} start={start}: {exc}")
                    break
                for path in collect_links(html, JOB_LINK_RE, "https://wuzzuf.net"):
                    rel = path.replace("https://wuzzuf.net", "")
                    if rel not in seen:
                        seen.add(rel)
                        paths.append(rel)
                        if len(paths) >= self.max_jobs:
                            break
        return paths[: self.max_jobs]

    def _parse_job_page(self, path: str, html: str, now: str) -> BronzeRecord | None:
        full_url = f"https://wuzzuf.net{path}" if path.startswith("/") else path
        ext_id = wuzzuf_external_id(path)
        ld = parse_job_posting_ld(html)
        og = parse_og_meta(html)

        if ld:
            title = strip_tags(str(ld.get("title") or ""))[:255]
            description = strip_tags(str(ld.get("description") or ""))[:5000]
            company = company_from_ld(ld)
            country, city = location_from_ld(ld)
        else:
            og_title = og.get("og:title", "")
            og_desc = og.get("og:description") or og.get("description", "")
            title, company, city = parse_wuzzuf_og_title(og_title)
            description = strip_tags(og_desc)[:5000]
            country = "Egypt"

        if not title or title == "Untitled":
            return None
        if not software_match(title, description):
            return None
        if len(description) < 40:
            description = (
                f"{title} at {company} in {city}, {country}. "
                "Software/IT role listed on Wuzzuf — apply on EmpowerWork."
            )

        text = f"{title} {description}"
        raw = {
            "title": title,
            "company_name": company,
            "company": company,
            "city": city or "Cairo",
            "country": country or "Egypt",
            "description": description,
            "url": full_url,
            "employment_type": employment_from_text(text),
            "remote_type": remote_from_text(text),
            "requirements": [],
            "job_category": "software",
        }
        return BronzeRecord(
            source=self.source_name,
            external_id=ext_id,
            source_url=full_url,
            fetched_at=now,
            raw=raw,
        )

    def fetch(self) -> List[BronzeRecord]:
        now = datetime.now(timezone.utc).isoformat()
        session = requests.Session()
        records: List[BronzeRecord] = []
        try:
            paths = self._collect_job_paths(session)
            for path in paths:
                try:
                    html = fetch_html(f"https://wuzzuf.net{path}", session)
                    rec = self._parse_job_page(path, html, now)
                    if rec:
                        records.append(rec)
                except Exception as exc:
                    print(f"  wuzzuf skip {path}: {exc}")
        except Exception as exc:
            print(f"  wuzzuf listing error: {exc}")
        if not records:
            print("  wuzzuf: 0 software jobs matched")
        return records

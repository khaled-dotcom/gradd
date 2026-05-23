"""Forasna connector — live scrape Egypt IT/software listings."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import requests

from .base import BaseConnector, BronzeRecord
from .scrape_common import (
    collect_links,
    company_from_ld,
    employment_from_text,
    fetch_html,
    forasna_external_id,
    location_from_ld,
    parse_job_posting_ld,
    parse_og_meta,
    remote_from_text,
    software_match,
    strip_tags,
)

FORASNA_BASE = "https://forasna.com"
JOB_LINK_RE = r'href="(https://forasna\.com/job/p/[^"?]+)"'
JOB_LINK_RE_REL = r'href="(/job/p/[^"?]+)"'


class ForasnaConnector(BaseConnector):
    source_name = "forasna"

    def __init__(self, lake_root, max_jobs: int = 50, config: dict | None = None):
        super().__init__(lake_root, max_jobs, config)
        self.list_pages = int(self.config.get("list_pages", 4))
        self.listing_path = self.config.get(
            "listing_path", "/jobs/egypt?category=it"
        )

    def _list_url(self, page: int) -> str:
        base = f"{FORASNA_BASE}{self.listing_path}"
        if page <= 1:
            return base
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}page={page}"

    def _collect_job_urls(self, session: requests.Session) -> List[str]:
        urls: List[str] = []
        seen = set()
        for page in range(1, self.list_pages + 1):
            if len(urls) >= self.max_jobs:
                break
            list_url = self._list_url(page)
            try:
                html = fetch_html(list_url, session)
            except Exception as exc:
                print(f"  forasna list page={page}: {exc}")
                break
            batch = collect_links(html, JOB_LINK_RE, FORASNA_BASE)
            if not batch:
                batch = [
                    FORASNA_BASE + p
                    for p in collect_links(html, JOB_LINK_RE_REL, FORASNA_BASE)
                ]
            for u in batch:
                if u not in seen:
                    seen.add(u)
                    urls.append(u)
                    if len(urls) >= self.max_jobs:
                        break
        return urls[: self.max_jobs]

    def fetch(self) -> List[BronzeRecord]:
        now = datetime.now(timezone.utc).isoformat()
        session = requests.Session()
        records: List[BronzeRecord] = []

        try:
            job_urls = self._collect_job_urls(session)
            for job_url in job_urls:
                try:
                    html = fetch_html(job_url, session)
                    ld = parse_job_posting_ld(html)
                    og = parse_og_meta(html)

                    if ld:
                        title = strip_tags(str(ld.get("title") or ""))[:255]
                        description = strip_tags(str(ld.get("description") or ""))[:5000]
                        company = company_from_ld(ld)
                        country, city = location_from_ld(ld)
                    else:
                        title = strip_tags(og.get("og:title", ""))[:255]
                        description = strip_tags(
                            og.get("og:description") or og.get("description", "")
                        )[:5000]
                        company = "Unknown"
                        country, city = "Egypt", "Cairo"

                    if not title:
                        continue
                    if not software_match(title, description):
                        continue
                    if len(description) < 40:
                        description = (
                            f"{title} — {company}, {city}. IT role on Forasna — apply on EmpowerWork."
                        )

                    text = f"{title} {description}"
                    raw = {
                        "title": title,
                        "company_name": company,
                        "company": company,
                        "city": city or "Cairo",
                        "country": country or "Egypt",
                        "description": description,
                        "url": job_url,
                        "employment_type": employment_from_text(text),
                        "remote_type": remote_from_text(text),
                        "requirements": [],
                        "job_category": "software",
                    }
                    records.append(
                        BronzeRecord(
                            source=self.source_name,
                            external_id=forasna_external_id(job_url),
                            source_url=job_url,
                            fetched_at=now,
                            raw=raw,
                        )
                    )
                except Exception as exc:
                    print(f"  forasna skip: {exc}")
        except Exception as exc:
            print(f"  forasna listing error: {exc}")

        if not records:
            print("  forasna: 0 software jobs matched")
        return records

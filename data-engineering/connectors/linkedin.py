"""
LinkedIn connector — guest API (public job search, Egypt + software keywords).

Uses LinkedIn's unauthenticated jobs-guest endpoints. May break if LinkedIn changes
their HTML/API. Enable only if you accept LinkedIn Terms of Service risk.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List
import requests
from bs4 import BeautifulSoup

from .base import BaseConnector, BronzeRecord
from .scrape_common import (
    employment_from_text,
    fetch_html,
    load_software_config,
    remote_from_text,
    software_match,
    strip_tags,
)

SEARCH_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
JOB_API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
JOB_VIEW = "https://www.linkedin.com/jobs/view/{job_id}"


class LinkedInConnector(BaseConnector):
    source_name = "linkedin"

    def __init__(self, lake_root, max_jobs: int = 50, config: dict | None = None):
        super().__init__(lake_root, max_jobs, config)
        self.location = self.config.get("location", "Egypt")
        self.list_pages = int(self.config.get("list_pages", 5))
        self.page_size = int(self.config.get("page_size", 25))
        sw = load_software_config()
        self.keywords: List[str] = sw.get("search_queries", {}).get(
            "linkedin",
            ["software engineer", "python developer"],
        )

    def _search_page(self, session: requests.Session, keyword: str, start: int) -> str:
        params = {
            "keywords": keyword,
            "location": self.location,
            "start": start,
            "f_TPR": "r604800",
        }
        sess = session
        sess.headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        resp = sess.get(SEARCH_API, params=params, timeout=25)
        resp.raise_for_status()
        return resp.text

    def _job_ids_from_html(self, html: str) -> List[str]:
        ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
        if not ids:
            ids = re.findall(r"/jobs/view/(\d+)", html)
        return list(dict.fromkeys(ids))

    def _collect_job_ids(self, session: requests.Session) -> List[str]:
        seen: List[str] = []
        seen_set = set()
        for keyword in self.keywords:
            if len(seen) >= self.max_jobs:
                break
            for page in range(self.list_pages):
                if len(seen) >= self.max_jobs:
                    break
                start = page * self.page_size
                try:
                    html = self._search_page(session, keyword, start)
                except Exception as exc:
                    print(f"  linkedin search '{keyword}' start={start}: {exc}")
                    break
                for jid in self._job_ids_from_html(html):
                    if jid not in seen_set:
                        seen_set.add(jid)
                        seen.append(jid)
                        if len(seen) >= self.max_jobs:
                            break
        return seen[: self.max_jobs]

    def _parse_job_detail(self, job_id: str, html: str, now: str) -> BronzeRecord | None:
        soup = BeautifulSoup(html, "html.parser")
        title_el = soup.select_one("h1, .top-card-layout__title, .topcard__title")
        title = strip_tags(title_el.get_text() if title_el else "")[:255]
        if not title:
            return None

        company_el = soup.select_one(
            ".topcard__org-name-link, .topcard__flavor, a[data-tracking-control-name='public_jobs_topcard-org-name']"
        )
        company = strip_tags(company_el.get_text() if company_el else "Unknown")[:255]

        loc_el = soup.select_one(".topcard__flavor--bullet, .topcard__flavor")
        location_text = ""
        for el in soup.select(".topcard__flavor"):
            t = strip_tags(el.get_text())
            if t and t != company and "," in t or "Egypt" in t:
                location_text = t
                break
        city = "Cairo"
        if location_text:
            city = location_text.split(",")[0].strip()[:100]

        desc_el = soup.select_one(
            ".show-more-less-html__markup, .description__text, .core-section-container__content"
        )
        description = strip_tags(desc_el.get_text() if desc_el else "")[:5000]
        if len(description) < 40:
            description = f"{title} at {company} in {location_text or 'Egypt'}."

        if not software_match(title, description):
            return None

        text = f"{title} {description}"
        view_url = JOB_VIEW.format(job_id=job_id)
        raw = {
            "title": title,
            "company_name": company,
            "company": company,
            "city": city,
            "country": "Egypt",
            "description": description,
            "url": view_url,
            "employment_type": employment_from_text(text),
            "remote_type": remote_from_text(text),
            "requirements": [],
            "job_category": "software",
        }
        return BronzeRecord(
            source=self.source_name,
            external_id=job_id,
            source_url=view_url,
            fetched_at=now,
            raw=raw,
        )

    def fetch(self) -> List[BronzeRecord]:
        now = datetime.now(timezone.utc).isoformat()
        session = requests.Session()
        records: List[BronzeRecord] = []
        try:
            job_ids = self._collect_job_ids(session)
            for jid in job_ids:
                try:
                    url = JOB_API.format(job_id=jid)
                    html = fetch_html(url, session)
                    rec = self._parse_job_detail(jid, html, now)
                    if rec:
                        records.append(rec)
                except Exception as exc:
                    print(f"  linkedin skip {jid}: {exc}")
        except Exception as exc:
            print(f"  linkedin error: {exc}")
        if not records:
            print("  linkedin: 0 software jobs (guest API may be blocked)")
        return records

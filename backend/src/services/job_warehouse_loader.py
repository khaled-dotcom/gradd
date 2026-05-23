"""
Load Gold Parquet from data lake into MySQL (OLTP).
Run: python -m backend.src.services.job_warehouse_loader
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.src.db.database import SessionLocal
from backend.src.db import models

REPO_ROOT = Path(__file__).resolve().parents[3]


def _latest_gold_dir() -> Optional[Path]:
    gold = REPO_ROOT / "data" / "lake" / "jobs" / "gold"
    if not gold.exists():
        return None
    dirs = sorted([d for d in gold.iterdir() if d.is_dir()])
    return dirs[-1] if dirs else None


def _get_or_create_company(db: Session, name: str) -> models.Company:
    company = db.query(models.Company).filter(models.Company.name == name).first()
    if not company:
        company = models.Company(name=name[:255])
        db.add(company)
        db.flush()
    return company


def _map_disability_tags(db: Session, job: models.Job, tags) -> None:
    """Link job to disabilities when ingest tags match known disability names."""
    if tags is None:
        return
    if hasattr(tags, "tolist"):
        tags = tags.tolist()
    if isinstance(tags, (list, tuple)) and len(tags) == 0:
        return
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = [tags]
    if not isinstance(tags, list):
        return
    disabilities = db.query(models.Disability).all()
    matched = []
    for tag in tags[:10]:
        t = str(tag).lower().strip()
        if not t:
            continue
        for d in disabilities:
            name = (d.name or "").lower()
            if t in name or name in t:
                matched.append(d)
                break
    if matched:
        job.disabilities = list({d.id: d for d in matched}.values())


def _get_or_create_location(db: Session, city: str, country: str) -> models.Location:
    city = city or "Cairo"
    country = country or "Egypt"
    loc = (
        db.query(models.Location)
        .filter(models.Location.city == city, models.Location.country == country)
        .first()
    )
    if not loc:
        loc = models.Location(city=city[:100], country=country[:100])
        db.add(loc)
        db.flush()
    return loc


def load_gold_to_mysql(run_id: Optional[str] = None) -> dict:
    try:
        import pandas as pd
    except ImportError as e:
        raise RuntimeError("pandas required for gold loader") from e

    gold_dir = _latest_gold_dir()
    if not gold_dir:
        return {"status": "no_gold", "added": 0, "updated": 0}

    parquet_file = gold_dir / "jobs.parquet"
    df = pd.read_parquet(parquet_file if parquet_file.exists() else gold_dir)
    run_id = run_id or str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception as e:
        db.close()
        return {
            "status": "db_unavailable",
            "added": 0,
            "updated": 0,
            "error": str(e),
            "gold_dir": str(gold_dir),
        }
    run = models.ImportRun(run_id=run_id, source="all", status="running")
    db.add(run)
    db.commit()

    added = updated = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seen_keys = set()

    try:
        for _, row in df.iterrows():
            source = str(row.get("source") or "unknown")
            external_id = str(row.get("external_id") or "")
            if not external_id:
                continue
            key = (source, external_id)
            seen_keys.add(key)

            job = (
                db.query(models.Job)
                .filter(models.Job.source == source, models.Job.external_id == external_id)
                .first()
            )
            company = _get_or_create_company(db, str(row.get("company_name") or "Unknown"))
            location = _get_or_create_location(
                db, str(row.get("city") or "Cairo"), str(row.get("country") or "Egypt")
            )

            fields = {
                "title": str(row.get("title") or "Untitled")[:255],
                "description": str(row.get("description") or "")[:5000],
                "employment_type": str(row.get("employment_type") or "full-time"),
                "remote_type": str(row.get("remote_type") or "remote"),
                "company_id": company.id,
                "location_id": location.id,
                "source_url": str(row.get("source_url") or "")[:1000],
                "content_hash": str(row.get("content_hash") or ""),
                "country": str(row.get("country") or "Egypt")[:100],
                "city": str(row.get("city") or "")[:100],
                "is_accessible_focus": bool(row.get("is_accessible_focus")),
                "is_active": True,
                "last_seen_at": now,
                "updated_at": now,
            }

            if job:
                changed = job.content_hash != fields["content_hash"]
                for k, v in fields.items():
                    setattr(job, k, v)
                if changed:
                    updated += 1
            else:
                job = models.Job(
                    source=source,
                    external_id=external_id,
                    imported_at=now,
                    **fields,
                )
                db.add(job)
                db.flush()
                added += 1

            reqs = row.get("requirements")
            if isinstance(reqs, str):
                try:
                    reqs = json.loads(reqs)
                except json.JSONDecodeError:
                    reqs = []
            elif hasattr(reqs, "tolist"):
                reqs = reqs.tolist()
            if reqs is not None and len(reqs) > 0:
                db.query(models.JobRequirement).filter(
                    models.JobRequirement.job_id == job.id
                ).delete()
                for r in reqs[:20]:
                    db.add(
                        models.JobRequirement(
                            job_id=job.id, requirement=str(r)[:500]
                        )
                    )

            tags = row.get("disability_tags")
            _map_disability_tags(db, job, tags)

        # Deactivate imported jobs not seen in this gold batch (same sources)
        sources = {k[0] for k in seen_keys}
        for src in sources:
            active_jobs = (
                db.query(models.Job)
                .filter(models.Job.source == src, models.Job.is_active == True)
                .all()
            )
            for j in active_jobs:
                if (j.source, j.external_id) not in seen_keys:
                    j.is_active = False
                    j.updated_at = now

        run.status = "success"
        run.added = added
        run.jobs_updated = updated
        run.finished_at = now
        db.commit()
        return {"status": "success", "run_id": run_id, "added": added, "updated": updated}
    except Exception as e:
        db.rollback()
        run.status = "failed"
        run.errors = str(e)
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = load_gold_to_mysql()
    print(result)

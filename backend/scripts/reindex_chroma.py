"""
Rebuild ChromaDB job embeddings from MySQL (use on Azure when EVENTS_ENABLED=false).

  python backend/scripts/reindex_chroma.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import joinedload, selectinload

from backend.src.config import settings
from backend.src.db.database import SessionLocal
from backend.src.db import models
from backend.src.rag.embedder import get_embedding
from backend.src.rag.retriever import add_to_chroma, get_collection


def _job_text(job: models.Job) -> str:
    reqs = ", ".join(r.requirement for r in job.requirements) if job.requirements else ""
    dis = ", ".join(d.name for d in job.disabilities) if job.disabilities else ""
    company = job.company.name if job.company else ""
    return f"{job.title}. {job.description}. Company: {company}. Requirements: {reqs}. Disability support: {dis}"


def main():
    if not settings.OPENAI_API_KEY:
        print("OPENAI_API_KEY is required for embeddings.")
        sys.exit(1)

    db = SessionLocal()
    try:
        jobs = (
            db.query(models.Job)
            .options(
                joinedload(models.Job.company),
                selectinload(models.Job.requirements),
                selectinload(models.Job.disabilities),
            )
            .all()
        )
        col = get_collection()
        if col:
            try:
                col.delete(where={})
            except Exception:
                pass

        n = 0
        for job in jobs:
            text = _job_text(job)
            vector = get_embedding(text)
            add_to_chroma(
                f"job_{job.id}",
                text,
                {"job_id": job.id, "title": job.title or ""},
                vector,
            )
            n += 1
            print(f"Indexed job {job.id}: {job.title}")

        print(f"Done. Indexed {n} jobs into Chroma ({settings.CHROMA_DIR}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

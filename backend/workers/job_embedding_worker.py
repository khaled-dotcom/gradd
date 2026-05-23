"""Index jobs into ChromaDB on JobCreated/JobUpdated events."""
from __future__ import annotations

import logging

from sqlalchemy.orm import joinedload, selectinload

from backend.src.config import settings
from backend.src.db.database import SessionLocal
from backend.src.db import models
from backend.src.events.schemas import EventEnvelope, EventType, Topics
from backend.src.rag.embedder import get_embedding
from backend.src.rag.retriever import add_to_chroma, get_collection
from backend.workers.base import run_consumer

logger = logging.getLogger(__name__)


def _job_text(job: models.Job) -> str:
    reqs = ", ".join(r.requirement for r in job.requirements) if job.requirements else ""
    dis = ", ".join(d.name for d in job.disabilities) if job.disabilities else ""
    company = job.company.name if job.company else ""
    return f"{job.title}. {job.description}. Company: {company}. Requirements: {reqs}. Disability support: {dis}"


def handle_event(event: EventEnvelope) -> None:
    if event.event_type == EventType.JOB_DELETED.value:
        job_id = event.payload.get("job_id")
        if not job_id:
            return
        try:
            col = get_collection()
            if col:
                col.delete(ids=[f"job_{job_id}"])
                logger.info("Deleted embedding for job %s", job_id)
        except Exception as e:
            logger.warning("Chroma delete failed: %s", e)
        return

    if event.event_type not in (
        EventType.JOB_CREATED.value,
        EventType.JOB_UPDATED.value,
    ):
        return

    job_id = event.payload.get("job_id")
    if not job_id:
        return

    if not settings.OPENAI_API_KEY:
        logger.info("Skipping embedding for job %s (no OPENAI_API_KEY)", job_id)
        return

    db = SessionLocal()
    try:
        job = (
            db.query(models.Job)
            .options(
                joinedload(models.Job.company),
                selectinload(models.Job.requirements),
                selectinload(models.Job.disabilities),
            )
            .filter(models.Job.id == job_id)
            .first()
        )
        if not job:
            return
        text = _job_text(job)
        vector = get_embedding(text)
        add_to_chroma(
            f"job_{job_id}",
            text,
            {"job_id": job_id, "title": job.title or ""},
            vector,
        )
        logger.info("Indexed job %s in ChromaDB", job_id)
    except Exception as e:
        logger.exception("Embedding worker failed for job %s: %s", job_id, e)
    finally:
        db.close()


if __name__ == "__main__":
    run_consumer([Topics.JOB], "embedding-workers", handle_event)

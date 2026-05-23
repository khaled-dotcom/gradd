"""Parse CV PDFs asynchronously after ApplicationSubmitted events."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.src.db.database import SessionLocal
from backend.src.db import models
from backend.src.events.producer import publish_event
from backend.src.events.schemas import EventEnvelope, EventType, Topics
from backend.src.utils.pdf_extractor import extract_cv_info
from backend.src.utils.blob_storage import read_upload_file, resolve_local_path
from io import BytesIO
from backend.workers.base import run_consumer

logger = logging.getLogger(__name__)


def _resolve_cv_path(cv_path: str) -> Path:
    p = Path(cv_path.lstrip("/"))
    if p.exists():
        return p
    alt = Path("uploads") / "cvs" / p.name
    if alt.exists():
        return alt
    return p


def handle_event(event: EventEnvelope) -> None:
    if event.event_type != EventType.APPLICATION_SUBMITTED.value:
        return

    app_id = event.payload.get("application_id")
    cv_path = event.payload.get("cv_path")
    if not app_id or not cv_path:
        return

    db = SessionLocal()
    try:
        application = db.query(models.JobApplication).filter(models.JobApplication.id == app_id).first()
        if not application:
            return

        extracted = {}
        raw = read_upload_file(cv_path)
        if raw:
            extracted = extract_cv_info(BytesIO(raw)) or {}
        else:
            path = _resolve_cv_path(cv_path)
            if path.exists():
                with open(path, "rb") as f:
                    extracted = extract_cv_info(f) or {}

        application.cv_extracted_info = json.dumps(extracted) if extracted else json.dumps({"parsed": False})
        db.commit()

        publish_event(
            Topics.APPLICATION,
            EventEnvelope(
                event_type=EventType.CV_PARSED.value,
                user_id=event.user_id,
                payload={
                    "application_id": app_id,
                    "job_id": event.payload.get("job_id"),
                    "extracted_info": extracted,
                },
            ),
        )
        logger.info("CV parsed for application %s", app_id)
    except Exception as e:
        logger.exception("CV worker failed for app %s: %s", app_id, e)
        publish_event(
            Topics.APPLICATION,
            EventEnvelope(
                event_type=EventType.APPLICATION_FAILED.value,
                user_id=event.user_id,
                payload={"application_id": app_id, "error": str(e)},
            ),
        )
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run_consumer([Topics.APPLICATION], "cv-workers", handle_event)

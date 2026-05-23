"""Process ChatRequested events and store answers in Redis."""
from __future__ import annotations

import logging

from backend.src.db.database import SessionLocal
from backend.src.events.producer import publish_event
from backend.src.events.redis_tasks import set_task
from backend.src.events.schemas import EventEnvelope, EventType, Topics
from backend.src.rag.rag_chat import chat_with_rag
from backend.src.services.chat_context import prepare_chat_context
from backend.workers.base import run_consumer

logger = logging.getLogger(__name__)


def handle_event(event: EventEnvelope) -> None:
    if event.event_type != EventType.CHAT_REQUESTED.value:
        return

    task_id = event.payload.get("task_id")
    message = event.payload.get("message")
    user_id = event.user_id
    if not task_id or not message:
        return

    db = SessionLocal()
    try:
        user_profile, relevant_jobs = prepare_chat_context(db, message, user_id)
        answer = chat_with_rag(message, user_profile, relevant_jobs)
        set_task(
            task_id,
            {"status": "completed", "answer": answer},
        )
        publish_event(
            Topics.CHAT,
            EventEnvelope(
                event_type=EventType.CHAT_COMPLETED.value,
                user_id=user_id,
                payload={"task_id": task_id, "answer": answer},
            ),
        )
        logger.info("Chat task %s completed", task_id)
    except Exception as e:
        logger.exception("Chat worker failed %s: %s", task_id, e)
        set_task(task_id, {"status": "failed", "error": str(e)})
        publish_event(
            Topics.CHAT,
            EventEnvelope(
                event_type=EventType.CHAT_FAILED.value,
                user_id=user_id,
                payload={"task_id": task_id, "error": str(e)},
            ),
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_consumer([Topics.CHAT], "chat-workers", handle_event)

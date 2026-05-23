from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.config import settings
from backend.src.events.producer import publish_event
from backend.src.events.redis_tasks import get_task, set_task
from backend.src.events.schemas import EventEnvelope, EventType, Topics
from backend.src.rag.rag_chat import chat_with_rag
from backend.src.services.chat_context import prepare_chat_context
from backend.src.utils.security import (
    sanitize_input, validate_string_length, validate_integer_id,
    check_rate_limit
)
from groq import Groq


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
def chat(
    request: Request,
    user_id: Optional[int] = Query(None),
    message: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"chat_{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment before chatting again.")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    message = sanitize_input(message, max_length=1000)
    if not validate_string_length(message, max_length=1000, min_length=1):
        raise HTTPException(status_code=400, detail="Invalid message length")

    if user_id and not validate_integer_id(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_profile, relevant_jobs = prepare_chat_context(db, message, user_id)
    answer = chat_with_rag(message, user_profile, relevant_jobs)
    return {"answer": answer}


@router.post("/async")
def chat_async(
    request: Request,
    user_id: Optional[int] = Query(None),
    message: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Enqueue chat to Kafka; poll GET /chat/result/{task_id} for the answer."""
    if not settings.EVENTS_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Async chat requires EVENTS_ENABLED=true and Kafka/Redis running.",
        )

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"chat_{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests.")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    message = sanitize_input(message, max_length=1000)
    if user_id and not validate_integer_id(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    task_id = str(uuid4())
    set_task(task_id, {"status": "pending", "message": message})

    event = EventEnvelope(
        event_type=EventType.CHAT_REQUESTED.value,
        user_id=user_id,
        payload={"task_id": task_id, "message": message},
    )
    if not publish_event(Topics.CHAT, event):
        raise HTTPException(status_code=503, detail="Could not enqueue chat task (Kafka unavailable).")

    return {"task_id": task_id, "status": "pending"}


@router.get("/result/{task_id}")
def chat_result(task_id: str):
    data = get_task(task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Task not found or expired")
    return data


@router.post("/speech-to-text")
async def speech_to_text(
    request: Request,
    file: UploadFile = File(...),
):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"chat_stt_{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail="Too many speech requests. Please wait a moment and try again."
        )

    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on the server.")

    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        client = Groq(api_key=settings.GROQ_API_KEY)
        transcription = client.audio.transcriptions.create(
            file=(file.filename or "audio.webm", contents),
            model="whisper-large-v3-turbo",
            temperature=0,
            response_format="verbose_json",
        )

        text = None
        if hasattr(transcription, "text"):
            text = transcription.text
        elif isinstance(transcription, dict):
            text = transcription.get("text")

        if text is None:
            text = ""

        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Groq STT error: {e}")
        raise HTTPException(status_code=500, detail="Error while processing audio. Please try again.")

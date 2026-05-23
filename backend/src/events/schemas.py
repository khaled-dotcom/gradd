"""Kafka event schemas for EmpowerWork."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Topics:
    APPLICATION = "application.events"
    JOB = "job.events"
    CHAT = "chat.events"
    ANALYTICS = "analytics.raw"


class EventType(str, Enum):
    APPLICATION_SUBMITTED = "ApplicationSubmitted"
    CV_PARSED = "CvParsed"
    APPLICATION_FAILED = "ApplicationFailed"
    JOB_CREATED = "JobCreated"
    JOB_UPDATED = "JobUpdated"
    JOB_DELETED = "JobDeleted"
    CHAT_REQUESTED = "ChatRequested"
    CHAT_COMPLETED = "ChatCompleted"
    CHAT_FAILED = "ChatFailed"


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    user_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "EventEnvelope":
        return cls.model_validate_json(raw)

"""Kafka event producer with graceful fallback when disabled or unavailable."""
from __future__ import annotations

import logging
from typing import Optional

from backend.src.config import settings
from backend.src.events.schemas import EventEnvelope, Topics

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    if not settings.EVENTS_ENABLED:
        return None
    try:
        from kafka import KafkaProducer

        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: v.encode("utf-8"),
            acks="all",
            retries=3,
        )
        return _producer
    except Exception as e:
        logger.warning("Kafka producer unavailable: %s", e)
        return None


def publish_event(topic: str, event: EventEnvelope) -> bool:
    """Publish event to Kafka. Returns True if sent, False if skipped/failed."""
    if not settings.EVENTS_ENABLED:
        return False
    producer = _get_producer()
    if producer is None:
        return False
    try:
        producer.send(topic, event.to_json())
        producer.flush(timeout=10)
        return True
    except Exception as e:
        logger.warning("Failed to publish %s: %s", event.event_type, e)
        return False


def topic_for_event(event_type: str) -> str:
    if event_type.startswith("Application") or event_type.startswith("Cv"):
        return Topics.APPLICATION
    if event_type.startswith("Job"):
        return Topics.JOB
    if event_type.startswith("Chat"):
        return Topics.CHAT
    return Topics.ANALYTICS

"""Shared Kafka consumer loop."""
from __future__ import annotations

import logging
import signal
import sys

from backend.src.config import settings
from backend.src.events.schemas import EventEnvelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_running = True


def _shutdown(*_):
    global _running
    _running = False


def run_consumer(topics: list[str], group_id: str, handler):
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
        group_id=group_id,
        value_deserializer=lambda m: m.decode("utf-8"),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    logger.info("Worker %s listening on %s", group_id, topics)
    try:
        while _running:
            records = consumer.poll(timeout_ms=1000)
            for _tp, messages in records.items():
                for msg in messages:
                    try:
                        event = EventEnvelope.from_json(msg.value)
                        handler(event)
                    except Exception as e:
                        logger.exception("Handler error: %s", e)
    finally:
        consumer.close()
        logger.info("Worker %s stopped", group_id)


if __name__ == "__main__":
    logger.error("Run a specific worker module, e.g. python -m backend.workers.cv_worker")
    sys.exit(1)

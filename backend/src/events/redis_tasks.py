"""Redis-backed async task status (chat jobs)."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from backend.src.config import settings

_redis = None


def _client():
    global _redis
    if _redis is not None:
        return _redis
    if not settings.EVENTS_ENABLED:
        return None
    try:
        import redis

        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis.ping()
        return _redis
    except Exception:
        return None


def set_task(task_id: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
    r = _client()
    if not r:
        return False
    key = f"chat:task:{task_id}"
    r.setex(key, ttl_seconds, json.dumps(data))
    return True


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    r = _client()
    if not r:
        return None
    raw = r.get(f"chat:task:{task_id}")
    if not raw:
        return None
    return json.loads(raw)

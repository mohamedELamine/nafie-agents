"""
Redis Bus — وكيل المحتوى
يستمع على content-events ويُطلق CONTENT_READY و CONTENT_PRODUCED.
المرجع: spec.md § ٢٢
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis as redis_lib

logger = logging.getLogger("content_agent.services.redis_bus")

# Streams
STREAM_CONTENT_EVENTS  = "content-events"
STREAM_PRODUCT_EVENTS  = "product-events"
STREAM_ANALYTICS_EVENTS = "analytics-events"

# Pub/Sub channels
CHANNEL_CONTENT_REQUESTS = "content-requests"
CHANNEL_SUPPORT_EVENTS   = "support-events"


class RedisBus:

    def __init__(self, redis_url: Optional[str] = None):
        url          = redis_url or os.environ["REDIS_URL"]
        self._client = redis_lib.from_url(url, decode_responses=True)

    # ── Publish ───────────────────────────────────────────────────

    def publish(self, channel: str, event: Dict) -> None:
        self._client.publish(channel, json.dumps(event, ensure_ascii=False))
        logger.debug("redis_bus.publish channel=%s event_type=%s", channel, event.get("event_type"))

    def publish_stream(self, stream: str, event: Dict) -> str:
        msg_id = self._client.xadd(stream, {"data": json.dumps(event, ensure_ascii=False)})
        logger.info(
            "redis_bus.stream stream=%s event_type=%s msg_id=%s",
            stream, event.get("event_type"), msg_id,
        )
        return msg_id

    # ── Event Builder ─────────────────────────────────────────────

    def build_event(
        self,
        event_type:     str,
        data:           Dict[str, Any],
        correlation_id: str,
        schema_version: str = "1.0",
        source:         str = "content_agent",
    ) -> Dict:
        return {
            "event_id":       str(uuid.uuid4()),
            "event_type":     event_type,
            "event_version":  schema_version,
            "source":         source,
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "data":           data,
        }

    # ── Consumer Group ────────────────────────────────────────────

    def ensure_consumer_group(self, stream: str, group: str) -> None:
        try:
            self._client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis_lib.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def read_group(
        self,
        stream:    str,
        group:     str,
        consumer:  str,
        count:     int = 10,
        block_ms:  int = 5000,
    ) -> List:
        result = self._client.xreadgroup(
            group, consumer, {stream: ">"}, count=count, block=block_ms,
        )
        return result or []

    def ack(self, stream: str, msg_id: str, group: str) -> None:
        self._client.xack(stream, group, msg_id)

    # ── Redis Checkpoint (للـ resume) ─────────────────────────────

    def save_checkpoint(self, key: str, data: Dict, ttl_seconds: int = 28800) -> None:
        """يحفظ checkpoint للـ workflow المعلّق (TTL افتراضي 8 ساعات)."""
        self._client.setex(key, ttl_seconds, json.dumps(data, ensure_ascii=False))

    def get_checkpoint(self, key: str) -> Optional[Dict]:
        raw = self._client.get(key)
        return json.loads(raw) if raw else None

    def delete_checkpoint(self, key: str) -> None:
        self._client.delete(key)

    def close(self) -> None:
        self._client.close()

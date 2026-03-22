"""
Redis Event Bus — T031–T033

الاستخدام:
  - Pub/Sub: للإشعارات غير الحرجة (نتائج جاهزة، statuses)
  - Streams: للأحداث الحرجة (product-events, sales-events) — مضمونة الاستلام

Event Envelope (contracts/events.md):
  event_id, event_type, schema_version, occurred_at, correlation_id, data

المرجع: docs/architecture.md § ٨
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger("platform_agent.services.redis_bus")

# ─── أسماء الـ Streams (تتطابق مع .env) ────────────────────
STREAM_THEME_EVENTS   = os.getenv("REDIS_STREAM_THEME_EVENTS",   "theme-events")
STREAM_PRODUCT_EVENTS = os.getenv("REDIS_STREAM_PRODUCT_EVENTS", "product-events")
STREAM_ASSET_EVENTS   = os.getenv("REDIS_STREAM_ASSET_EVENTS",   "asset-events")
STREAM_SALES_EVENTS   = os.getenv("REDIS_STREAM_SALES_EVENTS",   "sales-events")
CONSUMER_GROUP        = os.getenv("REDIS_CONSUMER_GROUP",         "platform-agent")


class RedisBus:
    """
    مشترك Redis واحد لكل instance.

    يُستحسن استخدامه كـ singleton داخل الـ agent process.
    """

    def __init__(self) -> None:
        self._redis = redis.from_url(
            os.environ["REDIS_URL"],
            decode_responses=True,
        )
        logger.info("RedisBus initialized | url=%s", os.environ["REDIS_URL"])

    # ─────────────────────────────────────────────────────────
    # T031 — publish (Pub/Sub)
    # ─────────────────────────────────────────────────────────

    def publish(self, channel: str, event: Dict[str, Any]) -> None:
        """
        نشر حدث على Redis Pub/Sub channel.

        مناسب للإشعارات غير الحرجة (reviews ready, asset notifications).
        لا ضمان الاستلام — إذا لم يكن هناك subscriber نشط، يُفقد الحدث.

        Args:
            channel: اسم الـ channel.
            event: dict الحدث (يُسلسَل إلى JSON).
        """
        payload = json.dumps(event, ensure_ascii=False, default=str)
        receivers = self._redis.publish(channel, payload)
        logger.debug(
            "redis.publish | channel=%s event_type=%s receivers=%s",
            channel,
            event.get("event_type"),
            receivers,
        )

    # ─────────────────────────────────────────────────────────
    # T032 — publish_stream (Redis Streams)
    # ─────────────────────────────────────────────────────────

    def publish_stream(self, stream: str, event: Dict[str, Any]) -> str:
        """
        نشر حدث حرج على Redis Stream.

        يضمن الاستلام من Consumer Groups — لا يُفقد حتى عند انقطاع الاتصال.

        Args:
            stream: اسم الـ stream (e.g., "product-events").
            event: dict الحدث.

        Returns:
            message_id المُولَّد من Redis.
        """
        # Redis Streams تستقبل dict — نُسلسل القيم
        message = {"data": json.dumps(event, ensure_ascii=False, default=str)}
        msg_id = self._redis.xadd(stream, message)
        logger.info(
            "redis.publish_stream | stream=%s msg_id=%s event_type=%s",
            stream,
            msg_id,
            event.get("event_type"),
        )
        return msg_id

    # ─────────────────────────────────────────────────────────
    # T033 — build_event (Event Envelope)
    # ─────────────────────────────────────────────────────────

    def build_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        schema_version: str = "1.0",
    ) -> Dict[str, Any]:
        """
        بناء Event Envelope موحد (contracts/events.md).

        القاعدة: `wp_post_id` يجب ألا يكون في data أبداً.

        Args:
            event_type: نوع الحدث (e.g., "NEW_PRODUCT_LIVE").
            data: بيانات الحدث الخاصة — بدون wp_post_id.
            correlation_id: ربط الأحداث المترابطة.
            schema_version: إصدار الـ schema (افتراضي "1.0").

        Returns:
            Event Envelope dict.
        """
        # ── حماية: لا wp_post_id في أي حدث صادر ─────────────
        if "wp_post_id" in data:
            logger.critical(
                "SECURITY: محاولة تضمين wp_post_id في حدث %s — مرفوض", event_type
            )
            data = {k: v for k, v in data.items() if k != "wp_post_id"}

        return {
            "event_id":       str(uuid.uuid4()),
            "event_type":     event_type,
            "schema_version": schema_version,
            "source":         "platform-agent",
            "occurred_at":    datetime.now(tz=timezone.utc).isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "data":           data,
        }

    # ─────────────────────────────────────────────────────────
    # Consumer Group Setup
    # ─────────────────────────────────────────────────────────

    def ensure_consumer_group(self, stream: str, group: str = CONSUMER_GROUP) -> None:
        """
        ينشئ Consumer Group إذا لم يكن موجوداً.

        يُستدعى عند بدء تشغيل الـ listeners.
        """
        try:
            self._redis.xgroup_create(stream, group, id="0", mkstream=True)
            logger.info("redis.ensure_consumer_group | stream=%s group=%s | CREATED", stream, group)
        except redis.exceptions.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug(
                    "redis.ensure_consumer_group | stream=%s group=%s | ALREADY EXISTS",
                    stream,
                    group,
                )
            else:
                raise

    def read_group(
        self,
        stream: str,
        group: str = CONSUMER_GROUP,
        consumer: str = "platform-1",
        count: int = 10,
        block_ms: int = 5000,
    ) -> list:
        """
        قراءة رسائل من Stream كـ Consumer Group member.

        Args:
            stream: اسم الـ stream.
            group: اسم الـ consumer group.
            consumer: اسم هذا الـ consumer (يُميّزه عن الآخرين).
            count: عدد الرسائل في كل قراءة.
            block_ms: مهلة الانتظار بالمللي ثانية.

        Returns:
            قائمة من [(stream, [(id, data)])]
        """
        return self._redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        ) or []

    def ack(self, stream: str, msg_id: str, group: str = CONSUMER_GROUP) -> None:
        """إقرار استلام الرسالة — يمنع إعادة معالجتها."""
        self._redis.xack(stream, group, msg_id)
        logger.debug("redis.ack | stream=%s msg_id=%s", stream, msg_id)

    # ─────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────

    def close(self) -> None:
        self._redis.close()

    def __enter__(self) -> "RedisBus":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

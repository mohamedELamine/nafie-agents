"""
Content Listener — يستمع على Redis ويُشغّل الـ pipeline.
يتعامل مع:
  - NEW_PRODUCT_LIVE   → EMAIL_LAUNCH + MARKETING_COPY (متوازيان)
  - THEME_UPDATED_LIVE → EMAIL_UPDATE
  - RECURRING_ISSUE_DETECTED → KNOWLEDGE_ARTICLE
  - CONTENT_REQUEST    → On-Demand
المرجع: spec.md § ١٠، ١١
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from agent import run_content_pipeline
from core.contracts import (
    EVENT_CONTENT_REQUEST,
    EVENT_NEW_PRODUCT_LIVE,
    EVENT_THEME_UPDATED_LIVE,
    STREAM_CONTENT_EVENTS,
    STREAM_PRODUCT_EVENTS,
)
from db.connection import close_pool, init_pool
from models import (
    CONTENT_CATEGORY_MAP, ContentRequest, ContentTrigger, ContentType,
    parse_evidence_contract,
)
from services.redis_bus import RedisBus

logger = logging.getLogger("content_agent.listeners.content_listener")

CONSUMER_GROUP = "content-agent-group"
CONSUMER_NAME  = "content-agent-consumer-1"

AUTO_CONTENT_SUBSCRIPTIONS = {
    "NEW_PRODUCT_LIVE":          [ContentType.EMAIL_LAUNCH, ContentType.MARKETING_COPY],
    "THEME_UPDATED_LIVE":        [ContentType.EMAIL_UPDATE],
    "RECURRING_ISSUE_DETECTED":  [ContentType.KNOWLEDGE_ARTICLE],
}


class ContentListener:

    def __init__(self, redis_bus: Optional[RedisBus] = None, **pipeline_services):
        self._redis     = redis_bus or RedisBus()
        self._services  = pipeline_services
        self._running   = False

    def start(self) -> None:
        """يبدأ الاستماع على product-events و content-events."""
        init_pool()
        self._redis.ensure_consumer_group(STREAM_PRODUCT_EVENTS, CONSUMER_GROUP)
        self._redis.ensure_consumer_group(STREAM_CONTENT_EVENTS, CONSUMER_GROUP)
        self._running = True
        logger.info("content_listener.started")
        self._listen_loop()

    def stop(self) -> None:
        self._running = False
        close_pool()
        logger.info("content_listener.stopped")

    def _listen_loop(self) -> None:
        while self._running:
            try:
                self._poll_stream(STREAM_PRODUCT_EVENTS)
                self._poll_stream(STREAM_CONTENT_EVENTS)
            except Exception as exc:
                logger.error("content_listener.loop_error err=%s", exc)

    def _poll_stream(self, stream: str) -> None:
        messages = self._redis.read_group(
            stream   = stream,
            group    = CONSUMER_GROUP,
            consumer = CONSUMER_NAME,
            count    = 5,
            block_ms = 2000,
        )
        for stream_name, msgs in messages:
            for msg_id, fields in msgs:
                try:
                    raw   = fields.get("data", "{}")
                    event = json.loads(raw)
                    self._dispatch(event)
                    self._redis.ack(stream, msg_id, CONSUMER_GROUP)
                except Exception as exc:
                    logger.error(
                        "content_listener.msg_error stream=%s msg=%s err=%s",
                        stream, msg_id, exc,
                    )

    def _dispatch(self, event: dict) -> None:
        event_type = event.get("event_type", "")

        if event_type == EVENT_NEW_PRODUCT_LIVE:
            self._on_new_product_live(event)
        elif event_type == EVENT_THEME_UPDATED_LIVE:
            self._on_theme_updated_live(event)
        elif event_type == "RECURRING_ISSUE_DETECTED":
            self._on_recurring_issue_detected(event)
        elif event_type == EVENT_CONTENT_REQUEST:
            self._on_content_request(event)
        else:
            logger.debug("content_listener.skip event_type=%s", event_type)

    # ── Auto-Content Handlers ─────────────────────────────────────

    def _on_new_product_live(self, event: dict) -> None:
        """
        يُشغّل طلبَين متوازيَين: EMAIL_LAUNCH + MARKETING_COPY.
        لكل منهما idempotency_key مستقل.
        """
        data = event.get("data", {})
        for content_type in AUTO_CONTENT_SUBSCRIPTIONS["NEW_PRODUCT_LIVE"]:
            request = ContentRequest(
                request_id        = str(uuid.uuid4()),
                trigger           = ContentTrigger.EVENT,
                requester         = "event:NEW_PRODUCT_LIVE",
                content_type      = content_type,
                content_category  = CONTENT_CATEGORY_MAP[content_type],
                theme_slug        = data.get("theme_slug"),
                theme_contract    = data.get("theme_contract", {}),
                raw_context       = data,
                target_agent      = "marketing_agent",
                correlation_id    = event.get("correlation_id", str(uuid.uuid4())),
                priority          = "normal",
                output_mode       = "variants" if content_type == ContentType.MARKETING_COPY else "single",
                variant_count     = 3 if content_type == ContentType.MARKETING_COPY else 1,
                evidence_contract = None,
                created_at        = datetime.now(timezone.utc),
            )
            # تشغيل متوازٍ
            t = threading.Thread(
                target = run_content_pipeline,
                args   = (request,),
                kwargs = self._services,
                daemon = True,
            )
            t.start()
            logger.info(
                "content_listener.new_product_live type=%s slug=%s",
                content_type.value, data.get("theme_slug"),
            )

    def _on_theme_updated_live(self, event: dict) -> None:
        data    = event.get("data", {})
        request = ContentRequest(
            request_id        = str(uuid.uuid4()),
            trigger           = ContentTrigger.EVENT,
            requester         = "event:THEME_UPDATED_LIVE",
            content_type      = ContentType.EMAIL_UPDATE,
            content_category  = CONTENT_CATEGORY_MAP[ContentType.EMAIL_UPDATE],
            theme_slug        = data.get("theme_slug"),
            theme_contract    = None,
            raw_context       = data,
            target_agent      = "platform_agent",
            correlation_id    = event.get("correlation_id", str(uuid.uuid4())),
            priority          = "high",
            output_mode       = "single",
            variant_count     = 1,
            evidence_contract = None,
            created_at        = datetime.now(timezone.utc),
        )
        run_content_pipeline(request, **self._services)
        logger.info("content_listener.theme_updated slug=%s", data.get("theme_slug"))

    def _on_recurring_issue_detected(self, event: dict) -> None:
        data     = event.get("data", {})
        evidence = parse_evidence_contract(data.get("evidence_contract"))

        request = ContentRequest(
            request_id        = str(uuid.uuid4()),
            trigger           = ContentTrigger.EVENT,
            requester         = "event:RECURRING_ISSUE_DETECTED",
            content_type      = ContentType.KNOWLEDGE_ARTICLE,
            content_category  = CONTENT_CATEGORY_MAP[ContentType.KNOWLEDGE_ARTICLE],
            theme_slug        = data.get("theme_slug"),
            theme_contract    = None,
            raw_context       = data,
            target_agent      = "support_agent",
            correlation_id    = event.get("correlation_id", str(uuid.uuid4())),
            priority          = "normal",
            output_mode       = "single",
            variant_count     = 1,
            evidence_contract = evidence,
            created_at        = datetime.now(timezone.utc),
        )
        run_content_pipeline(request, **self._services)
        logger.info("content_listener.recurring_issue slug=%s", data.get("theme_slug"))

    # ── On-Demand Handler ─────────────────────────────────────────

    def _on_content_request(self, event: dict) -> None:
        data         = event.get("data", {})
        content_type_str = data.get("content_type")

        try:
            content_type = ContentType(content_type_str)
        except ValueError:
            logger.error("content_listener.unknown_type type=%s", content_type_str)
            return

        request = ContentRequest(
            request_id        = str(uuid.uuid4()),
            trigger           = ContentTrigger.ON_DEMAND,
            requester         = event.get("source", "unknown"),
            content_type      = content_type,
            content_category  = CONTENT_CATEGORY_MAP[content_type],
            theme_slug        = data.get("theme_slug"),
            theme_contract    = data.get("theme_contract"),
            raw_context       = data.get("context", {}),
            target_agent      = event.get("source", "platform_agent"),
            correlation_id    = event.get("correlation_id", str(uuid.uuid4())),
            priority          = data.get("priority", "normal"),
            output_mode       = data.get("output_mode", "single"),
            variant_count     = data.get("variant_count", 1),
            evidence_contract = parse_evidence_contract(data.get("evidence_contract")),
            created_at        = datetime.now(timezone.utc),
        )
        run_content_pipeline(request, **self._services)
        logger.info(
            "content_listener.on_demand type=%s requester=%s",
            content_type.value, event.get("source"),
        )

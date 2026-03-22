"""T065 — Redis Stream Listener: Update Workflow"""
from __future__ import annotations
import json
import logging
import os
from agent import build_update_graph
from services.redis_bus import RedisBus, STREAM_THEME_EVENTS, CONSUMER_GROUP
from state import PlatformStatus

logger = logging.getLogger("platform_agent.listeners.update")
CONSUMER_NAME = os.getenv("HOSTNAME", "platform-1") + "-update"

class UpdateListener:
    def __init__(self):
        self.redis_bus = RedisBus()
        self.graph = build_update_graph()
        # نستخدم consumer group مختلف لـ update listener
        self.group = CONSUMER_GROUP + "-update"
        self.redis_bus.ensure_consumer_group(STREAM_THEME_EVENTS)
        logger.info("UpdateListener ready — stream: %s", STREAM_THEME_EVENTS)

    def run(self):
        while True:
            try:
                messages = self.redis_bus.read_group(
                    STREAM_THEME_EVENTS, group=self.group,
                    consumer=CONSUMER_NAME, block_ms=100
                )
                for _, msgs in messages:
                    for msg_id, msg_data in msgs:
                        try:
                            event = json.loads(msg_data.get("data", "{}"))
                            if event.get("event_type") == "THEME_UPDATED":
                                self._handle_theme_updated(event)
                            self.redis_bus.ack(STREAM_THEME_EVENTS, msg_id, group=self.group)
                        except Exception as exc:
                            logger.error("UpdateListener | processing failed | %s", exc)
            except Exception as exc:
                logger.error("UpdateListener | poll error | %s", exc)

    def _handle_theme_updated(self, event: dict):
        data = event.get("data", {})
        theme_slug = data.get("theme_slug", "")
        new_version = data.get("new_version", "")
        logger.info("UpdateListener | THEME_UPDATED | theme=%s v%s", theme_slug, new_version)
        initial_state = {
            "incoming_event": event,
            "idempotency_key": f"update:{theme_slug}:{new_version}",
            "event_type": "THEME_UPDATED",
            "event_id": event.get("event_id", ""),
            "theme_slug": theme_slug,
            "new_version": new_version,
            "previous_version": None,
            "ls_product_id": None,
            "ls_single_variant": None,
            "ls_unlimited_variant": None,
            "wp_post_id": None,
            "wp_post_url": None,
            "package_path": data.get("package_path", ""),
            "changelog": data.get("changelog", {}),
            "eligible_buyers": [],
            "notification_results": None,
            "status": PlatformStatus.IDLE,
            "error_code": None,
            "error": None,
            "logs": [],
        }
        result = self.graph.invoke(initial_state)
        logger.info("UpdateListener | THEME_UPDATED done | theme=%s v%s status=%s",
                    theme_slug, new_version, result.get("status"))

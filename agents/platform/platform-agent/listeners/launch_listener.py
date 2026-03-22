"""
T054 — Redis Stream Listener: Launch Workflow
يستمع على theme-events لـ THEME_APPROVED وasset-events لـ THEME_ASSETS_READY.
"""
from __future__ import annotations
import json
import logging
import os
from agent import build_launch_graph
from services.redis_bus import RedisBus, STREAM_THEME_EVENTS, STREAM_ASSET_EVENTS, CONSUMER_GROUP
from state import PlatformStatus

logger = logging.getLogger("platform_agent.listeners.launch")
CONSUMER_NAME = os.getenv("HOSTNAME", "platform-1")

class LaunchListener:
    def __init__(self):
        self.redis_bus = RedisBus()
        self.graph = build_launch_graph()
        self.redis_bus.ensure_consumer_group(STREAM_THEME_EVENTS)
        self.redis_bus.ensure_consumer_group(STREAM_ASSET_EVENTS)
        logger.info("LaunchListener ready — streams: %s, %s", STREAM_THEME_EVENTS, STREAM_ASSET_EVENTS)

    def run(self):
        while True:
            try:
                self._poll_theme_events()
                self._poll_asset_events()
            except Exception as exc:
                logger.error("LaunchListener | poll error | %s", exc)

    def _poll_theme_events(self):
        messages = self.redis_bus.read_group(STREAM_THEME_EVENTS, consumer=CONSUMER_NAME, block_ms=100)
        for _, msgs in messages:
            for msg_id, msg_data in msgs:
                try:
                    event = json.loads(msg_data.get("data", "{}"))
                    if event.get("event_type") == "THEME_APPROVED":
                        self._handle_theme_approved(event)
                    self.redis_bus.ack(STREAM_THEME_EVENTS, msg_id)
                except Exception as exc:
                    logger.error("LaunchListener | THEME_APPROVED processing failed | %s", exc)

    def _poll_asset_events(self):
        messages = self.redis_bus.read_group(STREAM_ASSET_EVENTS, consumer=CONSUMER_NAME, block_ms=100)
        for _, msgs in messages:
            for msg_id, msg_data in msgs:
                try:
                    event = json.loads(msg_data.get("data", "{}"))
                    if event.get("event_type") in ("THEME_ASSETS_READY", "THEME_ASSETS_PARTIALLY_READY"):
                        self._handle_assets_ready(event)
                    self.redis_bus.ack(STREAM_ASSET_EVENTS, msg_id)
                except Exception as exc:
                    logger.error("LaunchListener | ASSETS processing failed | %s", exc)

    def _handle_theme_approved(self, event: dict):
        data = event.get("data", {})
        theme_slug = data.get("theme_slug", "")
        logger.info("LaunchListener | THEME_APPROVED | theme=%s", theme_slug)
        initial_state = {
            "incoming_event": event,
            "theme_slug": theme_slug,
            "version": data.get("version", ""),
            "idempotency_key": f"launch:{theme_slug}:{data.get('version','')}",
            "approved_event_id": event.get("event_id", ""),
            "theme_contract": data.get("theme_contract", {}),
            "package_path": data.get("package_path", ""),
            "collected_assets": {},
            "has_video": False,
            "asset_timeout_warning": False,
            "extension_used": False,
            "ls_product_id": None,
            "ls_variants": [],
            "vip_product_id": None,
            "wp_post_id": None,
            "wp_post_url": None,
            "draft_page_content": None,
            "page_blocks": None,
            "revision_count": 0,
            "human_decision": None,
            "human_edits": None,
            "revision_notes": None,
            "status": PlatformStatus.IDLE,
            "error_code": None,
            "error": None,
            "logs": [],
        }
        result = self.graph.invoke(initial_state)
        logger.info("LaunchListener | THEME_APPROVED done | theme=%s status=%s",
                    theme_slug, result.get("status"))

    def _handle_assets_ready(self, event: dict):
        data = event.get("data", {})
        ikey = data.get("idempotency_key", "")
        theme_slug = data.get("theme_slug", "")
        logger.info("LaunchListener | ASSETS_READY | theme=%s key=%s", theme_slug, ikey)
        # جلب الـ state من Redis checkpoint واستئناف الـ graph
        try:
            checkpoint_key = f"workflow:{ikey}:checkpoint"
            self.redis_bus._redis.delete(checkpoint_key)
        except Exception: pass
        # إعادة استدعاء الـ graph مع الـ assets الجاهزة
        resume_state = {
            "idempotency_key": ikey,
            "theme_slug": theme_slug,
            "version": ikey.split(":")[-1] if ikey else "",
            "collected_assets": data.get("assets", {}),
            "status": PlatformStatus.RUNNING,
            "incoming_event": {},
            "approved_event_id": "",
            "theme_contract": {},
            "package_path": "",
            "has_video": False, "asset_timeout_warning": False, "extension_used": False,
            "ls_product_id": None, "ls_variants": [], "vip_product_id": None,
            "wp_post_id": None, "wp_post_url": None,
            "draft_page_content": None, "page_blocks": None,
            "revision_count": 0, "human_decision": None, "human_edits": None, "revision_notes": None,
            "error_code": None, "error": None, "logs": [],
        }
        result = self.graph.invoke(resume_state)
        logger.info("LaunchListener | ASSETS_READY done | theme=%s status=%s", theme_slug, result.get("status"))

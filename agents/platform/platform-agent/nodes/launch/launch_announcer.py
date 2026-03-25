"""
Node: LAUNCH_ANNOUNCER — T052
يُطلق NEW_PRODUCT_LIVE على Redis Stream ويُرسل تأكيد الإطلاق.
المرجع: spec.md § ١٧ | tasks/phase3 § T052
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from core.contracts import EVENT_NEW_PRODUCT_LIVE, STREAM_PRODUCT_EVENTS
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.redis_bus import RedisBus
from services.resend_client import ResendClient
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.launch_announcer")
NODE_NAME = "LAUNCH_ANNOUNCER"

def make_launch_announcer_node(
    registry: ProductRegistry,
    redis_bus: RedisBus,
    resend: ResendClient,
):
    def launch_announcer_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        parsed = state.get("parsed", {})
        theme_slug = state["theme_slug"]
        theme_name_ar = parsed.get("theme_name_ar", theme_slug)
        wp_post_url = state.get("wp_post_url", "")
        ls_product_id = state.get("ls_product_id", "")

        # ── 1. إطلاق NEW_PRODUCT_LIVE على Redis Stream ──────
        event = redis_bus.build_event(
            event_type=EVENT_NEW_PRODUCT_LIVE,
            data={
                "theme_slug": theme_slug,
                "theme_name_ar": theme_name_ar,
                "version": state.get("version", "1.0.0"),
                "wp_post_url": wp_post_url,
                "ls_product_id": ls_product_id,
                "pricing": {"single": 29, "unlimited": 79, "vip": 299},
                "theme_contract": state.get("theme_contract", {}),
                "launched_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=state.get("approved_event_id"),
        )
        redis_bus.publish_stream(STREAM_PRODUCT_EVENTS, event)
        logger.info("LAUNCH_ANNOUNCER | NEW_PRODUCT_LIVE published | theme=%s", theme_slug)

        # ── 2. إيميل تأكيد لصاحب المشروع ─────────────────────
        try:
            resend.send_launch_confirmation(
                theme_name_ar=theme_name_ar,
                theme_slug=theme_slug,
                wp_post_url=wp_post_url,
                version=state.get("version", "1.0.0"),
            )
        except Exception as exc:
            logger.warning("LAUNCH_ANNOUNCER | email failed (non-critical) | %s", exc)

        result = {
            **state,
            "status": PlatformStatus.COMPLETED,
            "logs": state.get("logs",[]) + [
                f"LAUNCH_ANNOUNCER: NEW_PRODUCT_LIVE sent | theme={theme_slug} url={wp_post_url}"
            ],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("LAUNCH_ANNOUNCER | DONE | theme=%s | 🚀", theme_slug)
        return result
    return launch_announcer_node

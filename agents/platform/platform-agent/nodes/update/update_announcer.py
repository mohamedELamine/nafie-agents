"""Node: UPDATE_ANNOUNCER — T063 | يُطلق THEME_UPDATED_LIVE على Redis Stream"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.redis_bus import RedisBus, STREAM_PRODUCT_EVENTS
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.update_announcer")
NODE_NAME = "UPDATE_ANNOUNCER"

def make_update_announcer_node(registry: ProductRegistry, redis_bus: RedisBus):
    def update_announcer_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        notif = state.get("notification_results", {})
        event = redis_bus.build_event(
            event_type="THEME_UPDATED_LIVE",
            data={
                "theme_slug": state["theme_slug"],
                "new_version": state["new_version"],
                "previous_version": state.get("previous_version", ""),
                "is_security": state.get("changelog", {}).get("is_security", False),
                "buyers_notified": notif.get("sent", 0),
            },
            correlation_id=state.get("event_id"),
        )
        redis_bus.publish_stream(STREAM_PRODUCT_EVENTS, event)
        logger.info("UPDATE_ANNOUNCER | THEME_UPDATED_LIVE | theme=%s v%s", state["theme_slug"], state["new_version"])

        result = {
            **state,
            "status": PlatformStatus.COMPLETED,
            "logs": state.get("logs",[]) + ["UPDATE_ANNOUNCER: THEME_UPDATED_LIVE published"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        return result
    return update_announcer_node

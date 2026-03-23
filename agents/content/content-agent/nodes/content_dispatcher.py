"""
Node: CONTENT_DISPATCHER
يُرسل المحتوى للوكيل المُستلِم عبر Redis.
المرجع: spec.md § ٩، ٢٢
"""
from __future__ import annotations
import logging
from state import ContentState
from services.redis_bus import STREAM_ANALYTICS_EVENTS

logger = logging.getLogger("content_agent.nodes.content_dispatcher")

KNOWN_AGENTS = {"platform_agent", "marketing_agent", "support_agent", "analytics_agent"}

AGENT_CHANNEL_MAP = {
    "platform_agent":  "platform-events",
    "marketing_agent": "marketing-events",
    "support_agent":   "support-events",
}


def make_content_dispatcher_node(redis_bus):
    def content_dispatcher_node(state: ContentState) -> dict:
        piece   = state.get("content_piece")
        pieces  = state.get("content_pieces", [])
        request = state["request"]
        target  = request.target_agent

        if not piece:
            return {
                "status":      "failed",
                "error_code":  "CON_DISPATCH_FAILED",
                "error_detail": "لا content_piece للتسليم",
            }

        if target not in KNOWN_AGENTS:
            logger.warning("content_dispatcher.unknown_target target=%s", target)
            return {
                "status":      "failed",
                "error_code":  "CON_UNKNOWN_TARGET_AGENT",
                "error_detail": f"وكيل غير معروف: {target}",
            }

        # بناء CONTENT_READY event
        variants_data = None
        if len(pieces) > 1:
            variants_data = [
                {"label": p.variant_label, "body": p.body}
                for p in pieces
            ]

        event = redis_bus.build_event(
            event_type     = "CONTENT_READY",
            data           = {
                "content_id":       piece.content_id,
                "content_type":     piece.content_type.value if hasattr(piece.content_type, 'value') else str(piece.content_type),
                "theme_slug":       piece.theme_slug,
                "title":            piece.title,
                "body":             piece.body,
                "variants":         variants_data,
                "metadata":         piece.metadata,
                "validation_score": piece.validation_score,
                "request_id":       request.request_id,
            },
            correlation_id = request.correlation_id,
        )

        channel = AGENT_CHANNEL_MAP.get(target, f"{target}-events")
        redis_bus.publish(channel, event)

        # إشعار وكيل التحليل بكل مخرج
        analytics_event = redis_bus.build_event(
            event_type     = "CONTENT_PRODUCED",
            data           = {
                "content_id":       piece.content_id,
                "content_type":     piece.content_type.value if hasattr(piece.content_type, 'value') else str(piece.content_type),
                "theme_slug":       piece.theme_slug,
                "validation_score": piece.validation_score,
                "target_agent":     target,
            },
            correlation_id = request.correlation_id,
        )
        redis_bus.publish_stream(STREAM_ANALYTICS_EVENTS, analytics_event)

        logger.info(
            "content_dispatcher.sent req=%s target=%s channel=%s",
            request.request_id, target, channel,
        )
        return {"dispatch_status": "sent", "status": "dispatched"}

    return content_dispatcher_node

"""
Marketing Agent — LangGraph pipeline builder.
build_marketing_graph() assembles the ordered node sequence and wires
the dependency objects (DB connection pool, Redis, platform clients).
run_marketing_pipeline() executes the graph against a MarketingState.
"""
import os
from datetime import datetime
from typing import Any, Dict

from .db.connection import get_conn
from .logging_config import get_logger
from .nodes.analytics_consumer import make_analytics_consumer_node
from .nodes.asset_collector import make_asset_collector_node
from .nodes.calendar_scheduler import make_calendar_scheduler_node
from .nodes.campaign_recorder import make_campaign_recorder_node
from .nodes.channel_router import make_channel_router_node
from .nodes.paid_channel_gate import make_paid_channel_gate_node
from .nodes.platform_publisher import make_platform_publisher_node
from .nodes.readiness_aggregator import make_readiness_aggregator_node
from .nodes.rejection_handler import make_rejection_handler_node
from .services.facebook_client import FacebookClient
from .services.instagram_client import InstagramClient
from .services.redis_bus import RedisBus, get_redis_bus
from .services.resend_client import ResendClient
from .services.tiktok_client import TikTokClient
from .services.whatsapp_client import WhatsAppClient
from .state import MarketingState

logger = get_logger("agent")

# ── dependency helpers ────────────────────────────────────────────────────────

def _make_redis() -> RedisBus:
    return get_redis_bus(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


def _make_facebook() -> FacebookClient:
    return FacebookClient(os.environ.get("FACEBOOK_PAGE_TOKEN", ""))


def _make_instagram() -> InstagramClient:
    return InstagramClient(os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""))


def _make_tiktok() -> TikTokClient:
    return TikTokClient(os.environ.get("TIKTOK_ACCESS_TOKEN", ""))


def _make_whatsapp() -> WhatsAppClient:
    return WhatsAppClient(
        access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
        phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
    )


def _make_resend() -> ResendClient:
    return ResendClient(os.environ.get("RESEND_API_KEY", ""))


# ── graph builder ─────────────────────────────────────────────────────────────

def build_marketing_graph():
    """Assemble the marketing pipeline and return an ordered list of (name, fn) steps."""
    redis       = _make_redis()
    facebook    = _make_facebook()
    instagram   = _make_instagram()
    tiktok      = _make_tiktok()
    whatsapp    = _make_whatsapp()
    resend      = _make_resend()

    steps = [
        ("readiness_aggregator", make_readiness_aggregator_node(redis)),
        ("asset_collector",      make_asset_collector_node()),
        ("analytics_consumer",   make_analytics_consumer_node(redis)),
        ("channel_router",       make_channel_router_node()),
        ("paid_channel_gate",    make_paid_channel_gate_node(resend)),
        ("calendar_scheduler",   make_calendar_scheduler_node(redis)),
        ("platform_publisher",   make_platform_publisher_node(facebook, instagram, tiktok, whatsapp)),
        ("rejection_handler",    make_rejection_handler_node(resend)),
        ("campaign_recorder",    make_campaign_recorder_node(redis)),
    ]
    return steps


# ── pipeline runner ───────────────────────────────────────────────────────────

def run_marketing_pipeline(state: MarketingState) -> Dict[str, Any]:
    """Execute every node in sequence against the given state."""
    try:
        steps = build_marketing_graph()

        campaign_id = (
            state.current_campaign.campaign_id
            if state.current_campaign
            else "unknown"
        )
        logger.info(f"Starting marketing pipeline for campaign {campaign_id}")

        results: Dict[str, Any] = {}
        for step_name, step_fn in steps:
            logger.info(f"Executing step: {step_name}")
            result = step_fn(state)
            results[step_name] = result

            # Stop early if readiness check says not ready
            if step_name == "readiness_aggregator" and result.get("readiness_status") != "ready":
                logger.warning(
                    f"Campaign {campaign_id} not ready: {result.get('reason')}. "
                    "Pipeline halted."
                )
                return {
                    "success": False,
                    "campaign_id": campaign_id,
                    "halted_at": step_name,
                    "reason": result.get("reason"),
                }

        logger.info(f"Marketing pipeline completed for campaign {campaign_id}")
        return {
            "success": True,
            "results": results,
            "campaign_id": campaign_id,
        }

    except Exception as e:
        logger.error(f"Error running marketing pipeline: {e}")
        return {
            "success": False,
            "error": str(e),
            "campaign_id": (
                state.current_campaign.campaign_id
                if state.current_campaign
                else "unknown"
            ),
        }

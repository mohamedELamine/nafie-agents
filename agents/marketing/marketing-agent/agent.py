"""
Marketing Agent — LangGraph pipeline builder.
build_marketing_graph() assembles the ordered node sequence and wires
the dependency objects (DB connection pool, Redis, platform clients).
run_marketing_pipeline() executes the graph against a MarketingState.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType
from core.contracts import (
    EVENT_ANALYTICS_SIGNAL,
    EVENT_CAMPAIGN_LAUNCHED,
    EVENT_CONTENT_READY,
    EVENT_NEW_PRODUCT_LIVE,
    EVENT_THEME_ASSETS_READY,
    STREAM_ANALYTICS_SIGNALS,
    STREAM_ASSET_EVENTS,
    STREAM_CONTENT_EVENTS,
    STREAM_MARKETING_EVENTS,
    STREAM_PRODUCT_EVENTS,
)

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
    return ResendClient(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        owner_email=os.environ.get("OWNER_EMAIL", ""),
    )


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

            # Law VI: paid channels require user approval — skip publishing
            if step_name == "paid_channel_gate" and result.get("needs_user_approval"):
                logger.warning(
                    f"Campaign {campaign_id}: paid channels require user approval. "
                    "Skipping platform_publisher, proceeding to campaign_recorder."
                )
                # Skip platform_publisher — jump to campaign_recorder
                for skip_name, skip_fn in steps:
                    if skip_name == "campaign_recorder":
                        recorder_result = skip_fn(state)
                        results["campaign_recorder"] = recorder_result
                        break
                return {
                    "success": True,
                    "campaign_id": campaign_id,
                    "paid_channels_pending_approval": True,
                    "suggested_channels": result.get("suggested_channels", []),
                    "results": results,
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


# ── BaseAgent subclass ─────────────────────────────────────────────

class MarketingAgent(BaseAgent):
    """Marketing agent — inherits BaseAgent for Redis, heartbeats, and supervision."""

    agent_name = AgentName.MARKETING

    def __init__(self):
        super().__init__()
        self._stream_bus = _make_redis()
        self._stream_bridge_task: asyncio.Task | None = None
        self._campaign_state: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        await self.bus.connect(self.agent_name)
        await self.setup_handlers()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._stream_bridge_task = asyncio.create_task(self._stream_bridge_loop())
        logger.info(f"[{self.agent_name}] ✓ جاهز")
        try:
            await self.bus.listen()
        finally:
            if self._stream_bridge_task:
                self._stream_bridge_task.cancel()
                await asyncio.gather(self._stream_bridge_task, return_exceptions=True)
                self._stream_bridge_task = None

    async def stop(self) -> None:
        if self._stream_bridge_task:
            self._stream_bridge_task.cancel()
            await asyncio.gather(self._stream_bridge_task, return_exceptions=True)
            self._stream_bridge_task = None
        await super().stop()

    async def setup_handlers(self) -> None:
        self.bus.on(EventType.CONTENT_READY, self.run)
        self.bus.on(EventType.VISUAL_READY, self.run)

    async def run(self, event: BusinessEvent) -> None:
        try:
            state = MarketingState(**event["payload"])
            result = run_marketing_pipeline(state)
            if result.get("success"):
                await self.emit(
                    EventType.CAMPAIGN_SENT,
                    result,
                    trace_id=event.get("trace_id"),
                )
        except Exception as e:
            await self.emit_error(str(e), trace_id=event.get("trace_id"))

    async def _stream_bridge_loop(self) -> None:
        while self._running:
            try:
                await self._poll_stream(STREAM_PRODUCT_EVENTS)
                await self._poll_stream(STREAM_CONTENT_EVENTS)
                await self._poll_stream(STREAM_ASSET_EVENTS)
                await self._poll_stream(STREAM_ANALYTICS_SIGNALS)
            except Exception as exc:
                logger.error("marketing stream bridge error: %s", exc)
            await asyncio.sleep(0.1)

    async def _poll_stream(self, stream_name: str) -> None:
        messages = await asyncio.to_thread(
            self._stream_bus.read_group,
            stream_name,
            f"{stream_name}-bridge",
            10,
            200,
            ">",
        )
        for message in messages:
            message_id = message.pop("__message_id", None)
            await self._record_stream_event(stream_name, message)
            if message_id:
                await asyncio.to_thread(self._stream_bus.ack, stream_name, message_id)

    async def _record_stream_event(self, stream_name: str, message: Dict[str, Any]) -> None:
        event_type = message.get("event_type")
        data = message.get("data", {})
        if not isinstance(data, dict):
            data = {}
        theme_slug = data.get("theme_slug") or message.get("theme_slug")
        if not theme_slug:
            return

        campaign = self._campaign_state.setdefault(
            theme_slug,
            {
                "theme_slug": theme_slug,
                "product_live": False,
                "content_ready": None,
                "assets_ready": None,
                "best_channel": None,
                "best_time": None,
                "emitted": False,
                "correlation_id": message.get("correlation_id"),
            },
        )

        if stream_name == STREAM_PRODUCT_EVENTS and event_type == EVENT_NEW_PRODUCT_LIVE:
            campaign["product_live"] = True
            campaign["product_event"] = data
        elif stream_name == STREAM_CONTENT_EVENTS and event_type == EVENT_CONTENT_READY:
            campaign["content_ready"] = data
        elif stream_name == STREAM_ASSET_EVENTS and event_type == EVENT_THEME_ASSETS_READY:
            campaign["assets_ready"] = data
        elif stream_name == STREAM_ANALYTICS_SIGNALS and event_type == EVENT_ANALYTICS_SIGNAL:
            if data.get("best_channel"):
                campaign["best_channel"] = data["best_channel"]
            if data.get("best_time"):
                campaign["best_time"] = data["best_time"]

        if campaign["product_live"] and campaign["content_ready"]:
            await self._emit_campaign_ready(campaign)

    async def _emit_campaign_ready(self, campaign: Dict[str, Any]) -> None:
        if campaign["emitted"]:
            return

        now = datetime.now(timezone.utc)
        campaign_id = f"camp_{campaign['theme_slug']}_{int(now.timestamp())}"
        assets_ready = campaign.get("assets_ready") or {}
        payload = {
            "campaign_id": campaign_id,
            "theme_slug": campaign["theme_slug"],
            "content_id": campaign["content_ready"].get("content_id"),
            "asset_batch_id": assets_ready.get("batch_id"),
            "best_channel": campaign.get("best_channel"),
            "best_time": campaign.get("best_time"),
            "generated_at": now.isoformat(),
        }
        await self.emit(
            EventType.CAMPAIGN_SENT,
            payload,
            trace_id=campaign.get("correlation_id"),
        )
        self._stream_bus.publish_stream(
            STREAM_MARKETING_EVENTS,
            self._stream_bus.build_event(
                event_type=EVENT_CAMPAIGN_LAUNCHED,
                campaign_id=campaign_id,
                theme_slug=campaign["theme_slug"],
                data=payload,
            ),
        )
        campaign["emitted"] = True
        logger.info("marketing stream bridge emitted campaign %s for %s", campaign_id, campaign["theme_slug"])


if __name__ == "__main__":
    agent = MarketingAgent()
    asyncio.run(agent.start())

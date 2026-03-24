"""
Analytics Agent — BaseAgent subclass.
Wraps the scheduler-based workflows and integrates with the
shared Redis bus, heartbeats, and supervision.
Law V: analytics-agent is read-only — sends signals only, does not execute actions.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType
from core.contracts import (
    EVENT_ANALYTICS_SIGNAL,
    EVENT_CAMPAIGN_LAUNCHED,
    EVENT_POST_PUBLISHED,
    STREAM_ANALYTICS_SIGNALS,
    STREAM_MARKETING_EVENTS,
)

from .db.connection import close_pool, init_pool, is_pool_initialized
from .logging_config import get_logger
from .services.redis_bus import get_redis_bus
from .workflows.immediate_evaluator import ImmediateEvaluator

logger = get_logger("agent")


class AnalyticsAgent(BaseAgent):
    """Analytics agent — read-only, sends ANALYTICS_SIGNAL only."""

    agent_name = AgentName.ANALYTICS

    def __init__(self):
        super().__init__()
        self._owns_db_pool = False
        self._stream_bus = get_redis_bus(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        self._stream_bridge_task: asyncio.Task | None = None

    async def start(self) -> None:
        if not is_pool_initialized():
            init_pool(minconn=2, maxconn=10)
            self._owns_db_pool = True
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
            if self._owns_db_pool and is_pool_initialized():
                close_pool()
                self._owns_db_pool = False

    async def setup_handlers(self) -> None:
        for event_type in [
            EventType.TICKET_CREATED,
            EventType.TICKET_ESCALATED,
            EventType.CAMPAIGN_SENT,
            EventType.THEME_PUBLISHED,
        ]:
            self.bus.on(event_type, self.run)

    async def run(self, event: BusinessEvent) -> None:
        try:
            evaluator = ImmediateEvaluator()
            evaluator.evaluate(event)
            logger.info(f"Processed event: {event['event_type']}")
        except Exception as e:
            await self.emit_error(str(e), trace_id=event.get("trace_id"))

    async def _stream_bridge_loop(self) -> None:
        while self._running:
            try:
                messages = await asyncio.to_thread(
                    self._stream_bus.read_group,
                    STREAM_MARKETING_EVENTS,
                    "analytics-agent",
                    "analytics-stream-bridge",
                    10,
                    200,
                    ">",
                )
                for message in messages:
                    message_id = message.pop("__message_id", None)
                    await self._publish_signal_from_marketing(message)
                    if message_id:
                        await asyncio.to_thread(self._stream_bus.ack, STREAM_MARKETING_EVENTS, message_id)
            except Exception as exc:
                logger.error("analytics stream bridge error: %s", exc)
            await asyncio.sleep(0.1)

    async def _publish_signal_from_marketing(self, message: dict) -> None:
        event_type = message.get("event_type")
        if event_type not in {EVENT_CAMPAIGN_LAUNCHED, EVENT_POST_PUBLISHED}:
            return

        data = message.get("data", {})
        theme_slug = data.get("theme_slug") or message.get("theme_slug")
        if not theme_slug:
            return

        signal_type = "best_time" if event_type == EVENT_POST_PUBLISHED else "best_channel"
        signal_data = (
            {"best_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), "source_event": event_type}
            if signal_type == "best_time"
            else {"best_channel": data.get("channel", "facebook_page"), "source_event": event_type}
        )
        self._stream_bus.publish_stream(
            STREAM_ANALYTICS_SIGNALS,
            {
                "event_type": EVENT_ANALYTICS_SIGNAL,
                "source": "analytics_agent",
                "signal_id": f"sig_{theme_slug}_{signal_type}",
                "signal_type": signal_type,
                "priority": "immediate",
                "target_agent": "marketing_agent",
                "theme_slug": theme_slug,
                "data": signal_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("analytics stream bridge emitted %s for %s", signal_type, theme_slug)


if __name__ == "__main__":
    agent = AnalyticsAgent()
    asyncio.run(agent.start())

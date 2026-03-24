"""
Analytics Agent — BaseAgent subclass.
Wraps the scheduler-based workflows and integrates with the
shared Redis bus, heartbeats, and supervision.
Law V: analytics-agent is read-only — sends signals only, does not execute actions.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType

from .db.connection import close_pool, init_pool, is_pool_initialized
from .logging_config import get_logger
from .workflows.immediate_evaluator import ImmediateEvaluator

logger = get_logger("agent")


class AnalyticsAgent(BaseAgent):
    """Analytics agent — read-only, sends ANALYTICS_SIGNAL only."""

    agent_name = AgentName.ANALYTICS

    def __init__(self):
        super().__init__()
        self._owns_db_pool = False

    async def start(self) -> None:
        if not is_pool_initialized():
            init_pool(minconn=2, maxconn=10)
            self._owns_db_pool = True
        try:
            await super().start()
        finally:
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


if __name__ == "__main__":
    agent = AnalyticsAgent()
    asyncio.run(agent.start())

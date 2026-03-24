"""
Analytics Agent — BaseAgent subclass.
Wraps the scheduler-based workflows and integrates with the
shared Redis bus, heartbeats, and supervision.
Law V: analytics-agent is read-only — sends signals only, does not execute actions.
"""
import asyncio
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType

from .logging_config import get_logger
from .workflows.signal_generator import generate_signals_from_patterns
from .workflows.immediate_evaluator import ImmediateEvaluator

logger = get_logger("agent")


class AnalyticsAgent(BaseAgent):
    """Analytics agent — read-only, sends ANALYTICS_SIGNAL only."""

    agent_name = AgentName.ANALYTICS

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

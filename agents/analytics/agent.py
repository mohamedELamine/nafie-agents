"""
Entry point wrapper — analytics-agent.
يُستخدم من docker-compose: python -m agents.analytics.agent
"""
import sys
import os
import asyncio
import types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

# Register analytics_agent as a virtual package backed by analytics-agent/
_pkg = types.ModuleType("analytics_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "analytics_agent"
sys.modules.setdefault("analytics_agent", _pkg)

# Ensure root (for core.*) and agent dir are on path
sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from analytics_agent import agent as _agent_module

ImmediateEvaluator = _agent_module.ImmediateEvaluator


class AnalyticsAgent(_agent_module.AnalyticsAgent):
    async def run(self, event):
        try:
            evaluator = ImmediateEvaluator()
            evaluator.evaluate(event)
            _agent_module.logger.info(f"Processed event: {event['event_type']}")
        except Exception as exc:
            await self.emit_error(str(exc), trace_id=event.get("trace_id"))

if __name__ == "__main__":
    asyncio.run(AnalyticsAgent().start())

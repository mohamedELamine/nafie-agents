"""
Entry point wrapper — marketing-agent.
يُستخدم من docker-compose: python -m agents.marketing.agent
"""
import sys
import os
import asyncio
import types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marketing-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

_pkg = types.ModuleType("marketing_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "marketing_agent"
sys.modules.setdefault("marketing_agent", _pkg)

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from marketing_agent import agent as _agent_module

run_marketing_pipeline = _agent_module.run_marketing_pipeline


class MarketingAgent(_agent_module.MarketingAgent):
    async def run(self, event):
        try:
            state = _agent_module.MarketingState(**event["payload"])
            result = run_marketing_pipeline(state)
            if result.get("success"):
                await self.emit(
                    _agent_module.EventType.CAMPAIGN_SENT,
                    result,
                    trace_id=event.get("trace_id"),
                )
        except Exception as exc:
            await self.emit_error(str(exc), trace_id=event.get("trace_id"))

if __name__ == "__main__":
    asyncio.run(MarketingAgent().start())

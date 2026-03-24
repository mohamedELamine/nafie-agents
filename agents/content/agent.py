"""Entry point wrapper — content-agent."""
import sys
import os
import asyncio
import types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

_pkg = types.ModuleType("content_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "content_agent"
sys.modules.setdefault("content_agent", _pkg)

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from content_agent import agent as _agent_module

run_content_pipeline = _agent_module.run_content_pipeline


class ContentAgent(_agent_module.ContentAgent):
    async def run(self, event):
        try:
            request = _agent_module.ContentRequest(**event["payload"])
            result = run_content_pipeline(request)
            if result.get("status") == "completed":
                await self.emit(
                    _agent_module.EventType.CONTENT_READY,
                    result,
                    trace_id=event.get("trace_id"),
                )
        except Exception as exc:
            await self.emit_error(str(exc), trace_id=event.get("trace_id"))

if __name__ == "__main__":
    asyncio.run(ContentAgent().start())

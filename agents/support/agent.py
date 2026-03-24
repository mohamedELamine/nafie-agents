"""Entry point wrapper — support-agent."""
import sys
import os
import asyncio
import types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "support-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

_pkg = types.ModuleType("support_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "support_agent"
sys.modules.setdefault("support_agent", _pkg)

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from support_agent.agent import SupportAgent

if __name__ == "__main__":
    asyncio.run(SupportAgent().start())

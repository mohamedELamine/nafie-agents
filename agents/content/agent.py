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

from content_agent.agent import ContentAgent

if __name__ == "__main__":
    asyncio.run(ContentAgent().start())

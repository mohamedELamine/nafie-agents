"""
Entry point wrapper — marketing-agent.
يُستخدم من docker-compose: python -m agents.marketing.agent
"""
import sys, os, asyncio, types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "marketing-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

_pkg = types.ModuleType("marketing_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "marketing_agent"
sys.modules.setdefault("marketing_agent", _pkg)

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from marketing_agent.agent import MarketingAgent

if __name__ == "__main__":
    asyncio.run(MarketingAgent().start())

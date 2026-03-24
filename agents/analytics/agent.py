"""
Entry point wrapper — analytics-agent.
يُستخدم من docker-compose: python -m agents.analytics.agent
"""
import sys, os, asyncio, types

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

from analytics_agent.agent import AnalyticsAgent

if __name__ == "__main__":
    asyncio.run(AnalyticsAgent().start())

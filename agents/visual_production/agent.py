"""Entry point wrapper — visual-production-agent."""
import sys, os, asyncio, types

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visual-production-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..", "..")

_pkg = types.ModuleType("visual_production_agent")
_pkg.__path__    = [_AGENT_DIR]
_pkg.__package__ = "visual_production_agent"
sys.modules.setdefault("visual_production_agent", _pkg)

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

# visual-production uses a listener-based main, not BaseAgent
if __name__ == "__main__":
    from visual_production_agent.main import main
    asyncio.run(main())

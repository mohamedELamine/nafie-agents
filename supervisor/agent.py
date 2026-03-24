"""Entry point wrapper — supervisor-agent."""
import sys
import os
import asyncio

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervisor-agent")
_ROOT_DIR  = os.path.join(_AGENT_DIR, "..", "..")

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

# supervisor-agent/main.py uses flat imports, no relative imports
if __name__ == "__main__":
    from main import main
    asyncio.run(main())

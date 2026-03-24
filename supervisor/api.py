"""ASGI wrapper for supervisor-agent FastAPI app."""

import os
import sys

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervisor-agent")
_ROOT_DIR = os.path.join(_AGENT_DIR, "..", "..")

sys.path.insert(0, os.path.abspath(_AGENT_DIR))
sys.path.insert(0, os.path.abspath(_ROOT_DIR))

from api.main import app  # noqa: E402

__all__ = ["app"]

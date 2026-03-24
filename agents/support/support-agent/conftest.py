"""
Root conftest for support-agent tests.
Sets up a virtual Python package "support_agent" backed by the support-agent/
directory so that relative imports (from ..logging_config import ...) work
even though the directory name contains a hyphen.
"""
import sys
import os
import types
import logging
from unittest.mock import MagicMock

SA_DIR = os.path.dirname(os.path.abspath(__file__))


def _create_package(name: str, path: str, parent=None) -> types.ModuleType:
    pkg = types.ModuleType(name)
    pkg.__file__ = os.path.join(path, "__init__.py")
    pkg.__path__ = [path]
    pkg.__package__ = name
    pkg.__spec__ = None
    if parent is not None:
        short = name.rsplit(".", 1)[-1]
        setattr(parent, short, pkg)
    sys.modules[name] = pkg
    return pkg


# ── 1. Register the root package "support_agent" ──────────────────────────
sa_pkg = _create_package("support_agent", SA_DIR)

# ── 2. Mock transitive deps that logging_config needs (redis, RedisBus) ───
#    We stub them so importing logging_config itself doesn't require redis.
sys.modules.setdefault("redis", MagicMock())
sys.modules.setdefault("redis.exceptions", MagicMock())

# Stub out the db.redis_bus module so logging_config's import resolves
db_dir  = os.path.join(SA_DIR, "db")
sa_db   = _create_package("support_agent.db", db_dir, sa_pkg)

redis_bus_mock = MagicMock()
redis_bus_mock.RedisBus = MagicMock
sys.modules["support_agent.db.redis_bus"] = redis_bus_mock
sa_db.redis_bus = redis_bus_mock

# ── 3. Register subpackages support_agent.nodes and support_agent.db ──────
nodes_dir = os.path.join(SA_DIR, "nodes")
_create_package("support_agent.nodes", nodes_dir, sa_pkg)

# ── 4. Add SA_DIR to sys.path so bare "nodes.X" imports also work ─────────
if SA_DIR not in sys.path:
    sys.path.insert(0, SA_DIR)

"""
Root conftest for analytics-agent tests.

Sets up a virtual Python package "analytics_agent" so that relative imports
inside the workflows/ and db/ modules work correctly in test context.

Also pre-mocks all external-service and database submodules so tests that
import individual workflow files don't need a live DB or Redis connection.
"""
import sys
import os
import types
import logging
from contextlib import contextmanager
from unittest.mock import MagicMock

AA_DIR = os.path.dirname(os.path.abspath(__file__))  # analytics-agent/


# ── helpers ──────────────────────────────────────────────────────────────────

def _pkg(name: str, path: str, parent=None) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__file__ = os.path.join(path, "__init__.py")
    m.__path__ = [path]
    m.__package__ = name
    m.__spec__ = None
    if parent is not None:
        setattr(parent, name.rsplit(".", 1)[-1], m)
    sys.modules[name] = m
    return m


def _stub(name: str, parent_pkg=None, **attrs) -> MagicMock:
    """Create a MagicMock module and register it in sys.modules."""
    m = MagicMock()
    for k, v in attrs.items():
        setattr(m, k, v)
    if parent_pkg is not None:
        short = name.rsplit(".", 1)[-1]
        setattr(parent_pkg, short, m)
    sys.modules[name] = m
    return m


# ── 1. Root package ───────────────────────────────────────────────────────────
aa = _pkg("analytics_agent", AA_DIR)

# ── 2. Subpackages (real paths) ───────────────────────────────────────────────
workflows_dir = os.path.join(AA_DIR, "workflows")
db_dir        = os.path.join(AA_DIR, "db")
services_dir  = os.path.join(AA_DIR, "services")

aa_workflows = _pkg("analytics_agent.workflows", workflows_dir, aa)
aa_db        = _pkg("analytics_agent.db",        db_dir,        aa)
aa_services  = _pkg("analytics_agent.services",  services_dir,  aa)

# ── 3. Stub DB submodules (avoid requiring a live PostgreSQL) ─────────────────
_stub("analytics_agent.db.event_store",       aa_db)
_stub("analytics_agent.db.signal_store",      aa_db)
_stub("analytics_agent.db.pattern_store",     aa_db)
_stub("analytics_agent.db.report_store",      aa_db)
_stub("analytics_agent.db.attribution_store", aa_db)
_stub("analytics_agent.db.metric_store",      aa_db)
_stub("analytics_agent.db.outcome_store",     aa_db)
# logging_config.py imports from .db.redis_bus (should be .services.redis_bus — bug in source)
_stub("analytics_agent.db.redis_bus",         aa_db, RedisBus=MagicMock)

# connection: provide a context-manager-compatible get_conn stub
_conn_mock = MagicMock()
@contextmanager
def _fake_get_conn():
    yield _conn_mock

conn_module = MagicMock()
conn_module.get_conn    = _fake_get_conn
conn_module.init_pool   = MagicMock()
conn_module.close_pool  = MagicMock()
sys.modules["analytics_agent.db.connection"] = conn_module
aa_db.connection = conn_module

# ── 4. Stub services submodules ───────────────────────────────────────────────
sys.modules.setdefault("redis",            MagicMock())
sys.modules.setdefault("redis.exceptions", MagicMock())
sys.modules.setdefault("httpx",            MagicMock())
sys.modules.setdefault("psycopg2",         MagicMock())
sys.modules.setdefault("psycopg2.pool",    MagicMock())

_stub("analytics_agent.services.redis_bus",      aa_services)
_stub("analytics_agent.services.resend_client",  aa_services)
_stub("analytics_agent.services.helpscout_client",    aa_services)
_stub("analytics_agent.services.lemon_squeezy_client", aa_services)
_stub("analytics_agent.services.product_registry",    aa_services)

# ── 5. Stub workflow sibling modules (avoid loading the whole __init__.py) ────
for wf in [
    "attribution", "immediate_evaluator", "metrics_engine",
    "pattern_analyzer", "reconciliation", "report_generator",
]:
    _stub(f"analytics_agent.workflows.{wf}", aa_workflows)

# ── 6. Add AA_DIR to sys.path so bare "workflows.X" imports also work ─────────
if AA_DIR not in sys.path:
    sys.path.insert(0, AA_DIR)

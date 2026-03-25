import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


AGENT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = AGENT_DIR.parents[2]

for path in (AGENT_DIR, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class _ModuleLoader:
    def __init__(self) -> None:
        self._original: dict[str, object | None] = {}

    def set_module(self, name: str, module: object) -> object:
        if name not in self._original:
            self._original[name] = sys.modules.get(name)
        sys.modules[name] = module
        return module

    def load_module(self, name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        self.set_module(name, module)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def restore(self) -> None:
        for name, original in reversed(list(self._original.items())):
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


@pytest.fixture
def mock_get_conn() -> callable:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    conn.cursor.return_value = cursor

    @contextmanager
    def _fake_get_conn():
        _fake_get_conn.calls += 1
        yield conn

    _fake_get_conn.conn = conn
    _fake_get_conn.cursor = cursor
    _fake_get_conn.calls = 0
    return _fake_get_conn


@pytest.fixture
def platform_env() -> SimpleNamespace:
    loader = _ModuleLoader()
    state_module = loader.load_module("state", AGENT_DIR / "state.py")

    db_pkg = types.ModuleType("db")
    db_pkg.__path__ = [str(AGENT_DIR / "db")]
    loader.set_module("db", db_pkg)

    idempotency = types.ModuleType("db.idempotency")
    idempotency.check_completed = MagicMock(return_value=False)
    idempotency.mark_started = MagicMock()
    idempotency.mark_completed = MagicMock()
    loader.set_module("db.idempotency", idempotency)
    db_pkg.idempotency = idempotency

    registry = types.ModuleType("db.registry")
    registry.ProductRegistry = object
    loader.set_module("db.registry", registry)
    db_pkg.registry = registry

    services_pkg = types.ModuleType("services")
    services_pkg.__path__ = [str(AGENT_DIR / "services")]
    loader.set_module("services", services_pkg)

    redis_bus = types.ModuleType("services.redis_bus")
    redis_bus.RedisBus = object
    loader.set_module("services.redis_bus", redis_bus)
    services_pkg.redis_bus = redis_bus

    resend_client = types.ModuleType("services.resend_client")
    resend_client.ResendClient = object
    loader.set_module("services.resend_client", resend_client)
    services_pkg.resend_client = resend_client

    yield SimpleNamespace(
        agent_dir=AGENT_DIR,
        load_module=loader.load_module,
        state=state_module,
        idempotency=idempotency,
    )

    loader.restore()


@pytest.fixture
def sample_product_event() -> dict:
    return {
        "idempotency_key": "launch:theme-one:1.0.0",
        "event_type": "THEME_APPROVED",
        "theme_slug": "theme-one",
        "version": "1.0.0",
        "approved_event_id": "evt_123",
        "incoming_event": {"event_id": "evt_123"},
        "theme_contract": {
            "theme_name_ar": "قالب تجريبي",
            "domain": "store",
            "cluster": "ecommerce",
            "build_version": "1.0.0",
            "woocommerce_enabled": True,
            "cod_enabled": True,
        },
        "parsed": {},
        "package_path": "/tmp/theme.zip",
        "collected_assets": {},
        "has_video": False,
        "asset_timeout_warning": False,
        "extension_used": False,
        "ls_product_id": "ls_123",
        "ls_variants": [],
        "vip_product_id": None,
        "wp_post_id": 123,
        "wp_post_url": "https://example.com/theme-one",
        "draft_page_content": None,
        "page_blocks": None,
        "revision_count": 0,
        "human_decision": None,
        "human_edits": None,
        "revision_notes": None,
        "status": None,
        "error_code": None,
        "error": None,
        "logs": [],
    }

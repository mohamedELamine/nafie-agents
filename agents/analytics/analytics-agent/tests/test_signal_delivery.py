"""
Smoke test: send_to_target_agent publishes to the shared analytics stream.

الـ setup يتم داخل دالة الاختبار حتى لا يؤثر على sys.modules
عند جمع الاختبارات من قِبَل pytest قبل تشغيل conftest.py.
"""
import importlib.util
import pathlib
import sys
import types
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.contracts import EVENT_ANALYTICS_SIGNAL, STREAM_ANALYTICS_SIGNALS

AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _pkg(name: str, path: pathlib.Path, parent: types.ModuleType | None = None) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path / "__init__.py")
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
    if parent is not None:
        setattr(parent, name.rsplit(".", 1)[-1], module)
    return module


def _module(name: str, parent: types.ModuleType | None = None, **attrs) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    if parent is not None:
        setattr(parent, name.rsplit(".", 1)[-1], module)
    return module


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@contextmanager
def _fake_conn():
    yield MagicMock()


def test_send_to_target_agent_publishes_signal_to_shared_stream():
    # ── تجهيز بيئة معزولة داخل الاختبار ──────────────────────────────────────
    # نحفظ مؤشرات sys.modules الأصلية ونستعيدها في النهاية
    _saved = {k: v for k, v in sys.modules.items() if k.startswith("analytics_agent")}
    try:
        aa = _pkg("analytics_agent", AGENT_ROOT)
        aa_workflows = _pkg("analytics_agent.workflows", AGENT_ROOT / "workflows", aa)
        aa_db = _pkg("analytics_agent.db", AGENT_ROOT / "db", aa)
        aa_services = _pkg("analytics_agent.services", AGENT_ROOT / "services", aa)

        _module("analytics_agent.logging_config", aa, get_logger=lambda name: MagicMock())
        _module(
            "analytics_agent.db.signal_store",
            aa_db,
            signal_sent_recently=MagicMock(return_value=False),
            save_signal=MagicMock(),
            mark_signal_sent=MagicMock(),
        )
        _module("analytics_agent.db.pattern_store", aa_db)
        _module("analytics_agent.db.report_store", aa_db)
        _module("analytics_agent.db.connection", aa_db, get_conn=_fake_conn)
        _module(
            "analytics_agent.services.redis_bus",
            aa_services,
            get_redis_bus=lambda redis_url=None: MagicMock(),
        )
        _module(
            "analytics_agent.services.resend_client",
            aa_services,
            send_owner_critical_alert=lambda **kwargs: True,
        )

        models = _load_module("analytics_agent.models", AGENT_ROOT / "models.py")
        aa.models = models
        signal_generator = _load_module(
            "analytics_agent.workflows.signal_generator",
            AGENT_ROOT / "workflows" / "signal_generator.py",
        )
        send_to_target_agent = signal_generator.send_to_target_agent

        # ── الاختبار ──────────────────────────────────────────────────────────
        signal = SimpleNamespace(
            signal_id="sig_1",
            signal_type=SimpleNamespace(value="best_time"),
            priority=SimpleNamespace(value="weekly"),
            target_agent="marketing_agent",
            theme_slug="theme-one",
            data={"best_time": "2026-01-02T12:00:00"},
            generated_at=SimpleNamespace(isoformat=lambda: "2026-01-02T12:00:00"),
            confidence=0.7,
            channel=None,
            recommendation="",
            supporting_pattern_id=None,
        )
        bus = MagicMock()

        signal_generator.get_conn = _fake_conn
        signal_generator.get_redis_bus = MagicMock(return_value=bus)
        signal_generator.signal_store.signal_sent_recently = MagicMock(return_value=False)
        signal_generator.signal_store.save_signal = MagicMock()
        signal_generator.signal_store.mark_signal_sent = MagicMock()

        send_to_target_agent(signal)

        bus.publish_stream.assert_called_once_with(
            STREAM_ANALYTICS_SIGNALS,
            {
                "event_type": EVENT_ANALYTICS_SIGNAL,
                "source": "analytics_agent",
                "signal_id": "sig_1",
                "signal_type": "best_time",
                "priority": "weekly",
                "target_agent": "marketing_agent",
                "theme_slug": "theme-one",
                "data": {"best_time": "2026-01-02T12:00:00"},
                "generated_at": "2026-01-02T12:00:00",
            },
        )
    finally:
        # ── استعادة sys.modules الأصلي ─────────────────────────────────────────
        for k in list(sys.modules.keys()):
            if k.startswith("analytics_agent"):
                del sys.modules[k]
        sys.modules.update(_saved)

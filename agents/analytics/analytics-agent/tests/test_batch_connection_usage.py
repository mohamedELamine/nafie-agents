import importlib.util
import pathlib
import sys
import types
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock


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


def test_generate_weekly_report_uses_shared_db_connection():
    # نحفظ حالة sys.modules ونستعيدها في النهاية لعزل هذا الاختبار
    _saved = {k: v for k, v in sys.modules.items() if k.startswith("analytics_agent")}
    try:
        analytics_agent = _pkg("analytics_agent", AGENT_ROOT)
        analytics_db = _pkg("analytics_agent.db", AGENT_ROOT / "db", analytics_agent)
        analytics_services = _pkg("analytics_agent.services", AGENT_ROOT / "services", analytics_agent)
        _pkg("analytics_agent.workflows", AGENT_ROOT / "workflows", analytics_agent)

        conn = MagicMock()

        @contextmanager
        def fake_get_conn():
            yield conn

        metric_store = _module(
            "analytics_agent.db.metric_store",
            analytics_db,
            get_period_metrics=MagicMock(return_value=[]),
        )
        event_store = _module(
            "analytics_agent.db.event_store",
            analytics_db,
            get_events=MagicMock(return_value=[{"raw_data": {"amount_usd": 12.5}}]),
        )
        pattern_store = _module(
            "analytics_agent.db.pattern_store",
            analytics_db,
            get_recent_patterns=MagicMock(return_value=[]),
        )
        report_store = _module(
            "analytics_agent.db.report_store",
            analytics_db,
            save_report=MagicMock(),
        )
        _module("analytics_agent.db.signal_store", analytics_db)
        _module(
            "analytics_agent.db.connection",
            analytics_db,
            get_conn=fake_get_conn,
        )
        _module(
            "analytics_agent.services.resend_client",
            analytics_services,
            send_weekly_report=lambda **kwargs: True,
        )
        _module(
            "analytics_agent.logging_config",
            analytics_agent,
            get_logger=lambda name: MagicMock(),
        )

        report_generator = _load_module(
            "analytics_agent.workflows.report_generator",
            AGENT_ROOT / "workflows" / "report_generator.py",
        )

        period_start = datetime(2026, 1, 1)
        period_end = datetime(2026, 1, 7)
        report = report_generator.generate_weekly_report(period_start, period_end)

        assert report is not None
        metric_store.get_period_metrics.assert_called_once_with(
            conn=conn,
            period_start=period_start,
            period_end=period_end,
            granularity="day",
        )
        event_store.get_events.assert_called_once_with(
            conn=conn,
            event_type="NEW_SALE",
            since=period_start,
            before=period_end,
            limit=1000,
        )
        pattern_store.get_recent_patterns.assert_called_once()
        report_store.save_report.assert_called_once_with(conn, report)
    finally:
        # استعادة sys.modules الأصلي بعد الاختبار
        for k in list(sys.modules.keys()):
            if k.startswith("analytics_agent"):
                del sys.modules[k]
        sys.modules.update(_saved)

import asyncio
import importlib.util
import pathlib
import sys
import types
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
VISUAL_ROOT = PROJECT_ROOT / "agents" / "visual_production" / "visual-production-agent"
MARKETING_ROOT = PROJECT_ROOT / "agents" / "marketing" / "marketing-agent"
ANALYTICS_ROOT = PROJECT_ROOT / "agents" / "analytics" / "analytics-agent"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _pkg(name: str, path: pathlib.Path, parent: types.ModuleType | None = None) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path / "__init__.py")
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
    if parent is not None:
        setattr(parent, name.rsplit(".", 1)[-1], module)
    return module


def test_theme_assets_ready_event_flows_into_marketing_listener():
    visual_manifest_builder = _load_module(
        "visual_manifest_builder_integration",
        VISUAL_ROOT / "nodes" / "manifest_builder.py",
    )
    redis_bus = MagicMock()
    redis_bus.build_event = AsyncMock(
        return_value={
            "event_type": "THEME_ASSETS_READY",
            "data": {"theme_slug": "theme-one", "assets": [{"asset_id": "batch_1_hero"}]},
        }
    )
    redis_bus.publish_stream = AsyncMock(return_value=True)

    asyncio.run(
        visual_manifest_builder.ManifestBuilderNode(redis_bus)(
            batch_id="batch_1",
            theme_slug="theme-one",
            approved_assets={
                "assets": [
                    {
                        "asset_id": "batch_1_hero",
                        "type": "hero",
                        "url": "https://cdn.example.com/hero.webp",
                        "size_kb": 128,
                        "quality_score": 0.95,
                    }
                ]
            },
        )
    )

    published_event = redis_bus.publish_stream.await_args.kwargs["data"]

    marketing_agent = _pkg("marketing_assets_integration", MARKETING_ROOT)
    marketing_db = _pkg("marketing_assets_integration.db", MARKETING_ROOT / "db", marketing_agent)
    _pkg("marketing_assets_integration.services", MARKETING_ROOT / "services", marketing_agent)
    _pkg("marketing_assets_integration.listeners", MARKETING_ROOT / "listeners", marketing_agent)

    fake_conn = MagicMock()
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.connect = lambda dsn: fake_conn
    sys.modules["psycopg2"] = psycopg2_stub

    logging_config = types.ModuleType("marketing_assets_integration.logging_config")
    logging_config.get_logger = lambda name: MagicMock()
    sys.modules["marketing_assets_integration.logging_config"] = logging_config

    campaign_log = types.ModuleType("marketing_assets_integration.db.campaign_log")
    campaign_log.save_log = MagicMock()
    sys.modules["marketing_assets_integration.db.campaign_log"] = campaign_log
    marketing_db.campaign_log = campaign_log

    marketing_bus = MagicMock()
    marketing_bus.read_group.return_value = [{**published_event, "__message_id": "2-0"}]
    services_module = sys.modules["marketing_assets_integration.services"]
    services_module.get_redis_bus = lambda redis_url=None: marketing_bus

    listener = _load_module(
        "marketing_assets_integration.listeners.assets_listener",
        MARKETING_ROOT / "listeners" / "assets_listener.py",
    )

    listener.make_assets_listener(None)()

    campaign_log.save_log.assert_called_once()
    logged_entry = campaign_log.save_log.call_args.args[1]
    assert logged_entry["event_type"] == "ASSETS_RECEIVED"
    assert logged_entry["details"]["data"]["theme_slug"] == "theme-one"
    marketing_bus.ack.assert_called_once_with("asset-events", "2-0")
    fake_conn.close.assert_called_once()


def test_analytics_signal_event_flows_into_marketing_listener():
    analytics_agent = _pkg("analytics_integration", ANALYTICS_ROOT)
    analytics_workflows = _pkg(
        "analytics_integration.workflows", ANALYTICS_ROOT / "workflows", analytics_agent
    )
    analytics_db = _pkg("analytics_integration.db", ANALYTICS_ROOT / "db", analytics_agent)
    analytics_services = _pkg(
        "analytics_integration.services", ANALYTICS_ROOT / "services", analytics_agent
    )

    logging_config = types.ModuleType("analytics_integration.logging_config")
    logging_config.get_logger = lambda name: MagicMock()
    sys.modules["analytics_integration.logging_config"] = logging_config

    signal_store = types.ModuleType("analytics_integration.db.signal_store")
    signal_store.signal_sent_recently = MagicMock(return_value=False)
    signal_store.save_signal = MagicMock()
    signal_store.mark_signal_sent = MagicMock()
    sys.modules["analytics_integration.db.signal_store"] = signal_store
    analytics_db.signal_store = signal_store

    connection = types.ModuleType("analytics_integration.db.connection")

    @contextmanager
    def fake_get_conn():
        yield MagicMock()

    connection.get_conn = fake_get_conn
    sys.modules["analytics_integration.db.connection"] = connection
    analytics_db.connection = connection

    sys.modules["analytics_integration.db.pattern_store"] = types.ModuleType(
        "analytics_integration.db.pattern_store"
    )
    sys.modules["analytics_integration.db.report_store"] = types.ModuleType(
        "analytics_integration.db.report_store"
    )

    redis_bus_module = types.ModuleType("analytics_integration.services.redis_bus")
    bus = MagicMock()
    redis_bus_module.get_redis_bus = MagicMock(return_value=bus)
    sys.modules["analytics_integration.services.redis_bus"] = redis_bus_module
    analytics_services.redis_bus = redis_bus_module

    resend_module = types.ModuleType("analytics_integration.services.resend_client")
    resend_module.send_owner_critical_alert = lambda **kwargs: True
    sys.modules["analytics_integration.services.resend_client"] = resend_module
    analytics_services.resend_client = resend_module

    models = _load_module("analytics_integration.models", ANALYTICS_ROOT / "models.py")
    analytics_agent.models = models

    signal_generator = _load_module(
        "analytics_integration.workflows.signal_generator",
        ANALYTICS_ROOT / "workflows" / "signal_generator.py",
    )

    signal = SimpleNamespace(
        signal_id="sig_1",
        signal_type=SimpleNamespace(value="best_channel"),
        priority=SimpleNamespace(value="weekly"),
        target_agent="marketing_agent",
        theme_slug="theme-one",
        data={"best_channel": "instagram"},
        generated_at=SimpleNamespace(isoformat=lambda: "2026-01-02T12:00:00"),
        confidence=0.7,
        channel=None,
        recommendation="",
        supporting_pattern_id=None,
    )

    signal_generator.send_to_target_agent(signal)
    _, published_event = bus.publish_stream.call_args.args

    marketing_agent = _pkg("marketing_analytics_integration", MARKETING_ROOT)
    marketing_db = _pkg("marketing_analytics_integration.db", MARKETING_ROOT / "db", marketing_agent)
    _pkg(
        "marketing_analytics_integration.services",
        MARKETING_ROOT / "services",
        marketing_agent,
    )
    _pkg(
        "marketing_analytics_integration.listeners",
        MARKETING_ROOT / "listeners",
        marketing_agent,
    )

    fake_conn = MagicMock()
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.connect = lambda dsn: fake_conn
    sys.modules["psycopg2"] = psycopg2_stub

    marketing_logging = types.ModuleType("marketing_analytics_integration.logging_config")
    marketing_logging.get_logger = lambda name: MagicMock()
    sys.modules["marketing_analytics_integration.logging_config"] = marketing_logging

    campaign_log = types.ModuleType("marketing_analytics_integration.db.campaign_log")
    campaign_log.save_log = MagicMock()
    sys.modules["marketing_analytics_integration.db.campaign_log"] = campaign_log
    marketing_db.campaign_log = campaign_log

    marketing_bus = MagicMock()
    marketing_bus.read_group.return_value = [{**published_event, "__message_id": "3-0"}]
    services_module = sys.modules["marketing_analytics_integration.services"]
    services_module.get_redis_bus = lambda redis_url=None: marketing_bus

    listener = _load_module(
        "marketing_analytics_integration.listeners.analytics_listener",
        MARKETING_ROOT / "listeners" / "analytics_listener.py",
    )

    listener.make_analytics_listener(None)()

    campaign_log.save_log.assert_called_once()
    logged_entry = campaign_log.save_log.call_args.args[1]
    assert logged_entry["event_type"] == "ANALYTICS_SIGNAL_RECEIVED"
    assert logged_entry["details"]["signal_type"] == "best_channel"
    marketing_bus.ack.assert_called_once_with("analytics:signals", "3-0")
    fake_conn.close.assert_called_once()

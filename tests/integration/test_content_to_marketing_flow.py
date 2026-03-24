import importlib.util
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT_ROOT = PROJECT_ROOT / "agents" / "content" / "content-agent"
MARKETING_ROOT = PROJECT_ROOT / "agents" / "marketing" / "marketing-agent"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CONTENT_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTENT_ROOT))


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


def test_content_ready_event_flows_into_marketing_listener():
    sys.modules.setdefault("redis", MagicMock())

    services_pkg = types.ModuleType("services")
    services_pkg.__path__ = [str(CONTENT_ROOT / "services")]
    redis_bus_stub = types.ModuleType("services.redis_bus")
    redis_bus_stub.STREAM_ANALYTICS_EVENTS = "analytics-events"
    services_pkg.redis_bus = redis_bus_stub
    sys.modules["services"] = services_pkg
    sys.modules["services.redis_bus"] = redis_bus_stub

    content_dispatcher = _load_module(
        "content_dispatcher_integration_under_test",
        CONTENT_ROOT / "nodes" / "content_dispatcher.py",
    )

    published_messages = []
    content_bus = MagicMock()
    content_bus.build_event.side_effect = lambda **kwargs: kwargs
    content_bus.publish_stream.side_effect = (
        lambda stream, event: published_messages.append((stream, event))
    )

    piece = SimpleNamespace(
        content_id="content_123",
        content_type=SimpleNamespace(value="marketing_copy"),
        theme_slug="theme-one",
        title="Launch copy",
        body="Arabic launch body",
        metadata={"locale": "ar"},
        validation_score=0.97,
    )
    request = SimpleNamespace(
        request_id="req_123",
        correlation_id="corr_123",
        target_agent="marketing_agent",
    )

    content_dispatcher.make_content_dispatcher_node(content_bus)(
        {
            "content_piece": piece,
            "content_pieces": [piece],
            "request": request,
        }
    )

    stream_name, event = published_messages[0]

    marketing_agent = _pkg("marketing_agent_integration", MARKETING_ROOT)
    marketing_db = _pkg("marketing_agent_integration.db", MARKETING_ROOT / "db", marketing_agent)
    _pkg("marketing_agent_integration.services", MARKETING_ROOT / "services", marketing_agent)
    _pkg("marketing_agent_integration.listeners", MARKETING_ROOT / "listeners", marketing_agent)

    fake_conn = MagicMock()
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.connect = lambda dsn: fake_conn
    sys.modules["psycopg2"] = psycopg2_stub

    logging_config = types.ModuleType("marketing_agent_integration.logging_config")
    logging_config.get_logger = lambda name: MagicMock()
    sys.modules["marketing_agent_integration.logging_config"] = logging_config

    campaign_log = types.ModuleType("marketing_agent_integration.db.campaign_log")
    campaign_log.save_log = MagicMock()
    sys.modules["marketing_agent_integration.db.campaign_log"] = campaign_log
    marketing_db.campaign_log = campaign_log

    marketing_bus = MagicMock()
    marketing_bus.read_group.return_value = [{**event, "__message_id": "1-0"}]
    services_module = sys.modules["marketing_agent_integration.services"]
    services_module.get_redis_bus = lambda redis_url=None: marketing_bus

    listener = _load_module(
        "marketing_agent_integration.listeners.content_listener",
        MARKETING_ROOT / "listeners" / "content_listener.py",
    )

    listener.make_content_listener(None)()

    assert stream_name == "content-events"
    campaign_log.save_log.assert_called_once()
    logged_entry = campaign_log.save_log.call_args.args[1]
    assert logged_entry["event_type"] == "CONTENT_RECEIVED"
    assert logged_entry["details"]["data"]["content_id"] == "content_123"
    marketing_bus.ack.assert_called_once_with("content-events", "1-0")
    fake_conn.close.assert_called_once()

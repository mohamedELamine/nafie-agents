import importlib.util
import pathlib
import sys
import types
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
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


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


marketing_agent = _pkg("marketing_agent", AGENT_ROOT)
marketing_agent_nodes = _pkg("marketing_agent.nodes", AGENT_ROOT / "nodes", marketing_agent)
marketing_agent_db = _pkg("marketing_agent.db", AGENT_ROOT / "db", marketing_agent)
marketing_agent_services = _pkg("marketing_agent.services", AGENT_ROOT / "services", marketing_agent)

sys.modules.setdefault("redis", MagicMock())
sys.modules.setdefault("redis.exceptions", MagicMock())
psycopg2_stub = MagicMock()
psycopg2_stub.extensions = SimpleNamespace(connection=object)
sys.modules.setdefault("psycopg2", psycopg2_stub)
sys.modules.setdefault("psycopg2.pool", MagicMock())

logging_config = types.ModuleType("marketing_agent.logging_config")
logging_config.get_logger = lambda name: MagicMock()
sys.modules["marketing_agent.logging_config"] = logging_config
marketing_agent.logging_config = logging_config

marketing_calendar = types.ModuleType("marketing_agent.db.marketing_calendar")
marketing_calendar.get_scheduled_posts = MagicMock()
marketing_calendar.save_campaign = MagicMock()
sys.modules["marketing_agent.db.marketing_calendar"] = marketing_calendar
marketing_agent_db.marketing_calendar = marketing_calendar

campaign_log = types.ModuleType("marketing_agent.db.campaign_log")
campaign_log.save_log = MagicMock()
sys.modules["marketing_agent.db.campaign_log"] = campaign_log
marketing_agent_db.campaign_log = campaign_log

connection = types.ModuleType("marketing_agent.db.connection")
connection.get_conn = lambda: None
sys.modules["marketing_agent.db.connection"] = connection
marketing_agent_db.connection = connection

redis_bus_module = types.ModuleType("marketing_agent.services.redis_bus")
redis_bus_module.RedisBus = object
sys.modules["marketing_agent.services.redis_bus"] = redis_bus_module
marketing_agent_services.redis_bus = redis_bus_module

from core.contracts import EVENT_CAMPAIGN_LAUNCHED, EVENT_POST_PUBLISHED, STREAM_MARKETING_EVENTS

campaign_recorder = _load_module(
    "marketing_agent.nodes.campaign_recorder",
    AGENT_ROOT / "nodes" / "campaign_recorder.py",
)
make_campaign_recorder_node = campaign_recorder.make_campaign_recorder_node


@contextmanager
def _fake_conn():
    yield MagicMock()


def test_campaign_recorder_emits_stream_events_for_published_posts():
    redis_bus = MagicMock()
    redis_bus.build_event.side_effect = lambda **kwargs: kwargs
    campaign_recorder.marketing_calendar.get_scheduled_posts.reset_mock()
    campaign_recorder.marketing_calendar.save_campaign.reset_mock()
    campaign_recorder.campaign_log.save_log.reset_mock()

    current_campaign = SimpleNamespace(
        campaign_id="camp_1",
        theme_slug="theme-one",
        title="Launch campaign",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 7),
    )
    state = SimpleNamespace(current_campaign=current_campaign)

    published_post = {
        "post_id": "post_1",
        "channel": "instagram",
        "format": "reel",
        "status": "published",
        "published_at": datetime(2026, 1, 2, 12, 0, 0),
        "scheduled_time": datetime(2026, 1, 2, 12, 0, 0),
    }

    campaign_recorder.get_conn = _fake_conn
    campaign_recorder.marketing_calendar.get_scheduled_posts.return_value = [published_post]

    result = make_campaign_recorder_node(redis_bus)(state)

    assert result["has_events"] is True

    published_call = (
        STREAM_MARKETING_EVENTS,
        {
            "event_type": EVENT_POST_PUBLISHED,
            "campaign_id": "camp_1",
            "theme_slug": "theme-one",
            "data": {
                "post_id": "post_1",
                "channel": "instagram",
                "format": "reel",
                "published_at": "2026-01-02T12:00:00",
            },
        },
    )
    launched_call = (
        STREAM_MARKETING_EVENTS,
        {
            "event_type": EVENT_CAMPAIGN_LAUNCHED,
            "campaign_id": "camp_1",
            "theme_slug": "theme-one",
            "data": {"published_posts": 1},
        },
    )

    assert published_call in [call.args for call in redis_bus.publish_stream.call_args_list]
    assert launched_call in [call.args for call in redis_bus.publish_stream.call_args_list]

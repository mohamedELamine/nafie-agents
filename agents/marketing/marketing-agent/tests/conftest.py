import importlib.util
import sys
import types
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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
        self._original: dict[str, types.ModuleType | None] = {}

    def set_module(self, name: str, module: types.ModuleType) -> types.ModuleType:
        if name not in self._original:
            self._original[name] = sys.modules.get(name)
        sys.modules[name] = module
        return module

    def make_package(
        self,
        name: str,
        path: Path,
        parent: types.ModuleType | None = None,
    ) -> types.ModuleType:
        module = types.ModuleType(name)
        module.__file__ = str(path / "__init__.py")
        module.__path__ = [str(path)]
        module.__package__ = name
        self.set_module(name, module)
        if parent is not None:
            setattr(parent, name.rsplit(".", 1)[-1], module)
        return module

    def load_module(self, name: str, path: Path) -> types.ModuleType:
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
def mock_redis_bus() -> MagicMock:
    bus = MagicMock()
    bus.publish_stream.return_value = True
    bus.read_group.return_value = []
    bus.ack.return_value = True
    bus.create_checkpoint.return_value = "checkpoint_123"
    bus.build_event.side_effect = lambda **kwargs: kwargs
    return bus


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
def marketing_env() -> SimpleNamespace:
    loader = _ModuleLoader()
    marketing_agent = loader.make_package("marketing_agent", AGENT_DIR)
    loader.make_package("marketing_agent.nodes", AGENT_DIR / "nodes", marketing_agent)
    marketing_db = loader.make_package("marketing_agent.db", AGENT_DIR / "db", marketing_agent)
    marketing_services = loader.make_package(
        "marketing_agent.services", AGENT_DIR / "services", marketing_agent
    )

    loader.set_module("redis", MagicMock())
    loader.set_module("redis.exceptions", MagicMock())

    psycopg2 = types.ModuleType("psycopg2")
    psycopg2.extensions = SimpleNamespace(connection=object)
    loader.set_module("psycopg2", psycopg2)
    loader.set_module("psycopg2.pool", MagicMock())

    logging_config = types.ModuleType("marketing_agent.logging_config")
    logging_config.get_logger = lambda name: MagicMock()
    loader.set_module("marketing_agent.logging_config", logging_config)
    marketing_agent.logging_config = logging_config

    models = loader.load_module("marketing_agent.models", AGENT_DIR / "models.py")
    state = loader.load_module("marketing_agent.state", AGENT_DIR / "state.py")

    marketing_calendar = types.ModuleType("marketing_agent.db.marketing_calendar")
    marketing_calendar.schedule_post = MagicMock()
    marketing_calendar.get_scheduled_posts = MagicMock(return_value=[])
    marketing_calendar.save_campaign = MagicMock()
    loader.set_module("marketing_agent.db.marketing_calendar", marketing_calendar)
    marketing_db.marketing_calendar = marketing_calendar

    campaign_log = types.ModuleType("marketing_agent.db.campaign_log")
    campaign_log.save_log = MagicMock()
    loader.set_module("marketing_agent.db.campaign_log", campaign_log)
    marketing_db.campaign_log = campaign_log

    connection = types.ModuleType("marketing_agent.db.connection")
    connection.get_conn = lambda: None
    loader.set_module("marketing_agent.db.connection", connection)
    marketing_db.connection = connection

    redis_bus_module = types.ModuleType("marketing_agent.services.redis_bus")
    redis_bus_module.RedisBus = object
    loader.set_module("marketing_agent.services.redis_bus", redis_bus_module)
    marketing_services.redis_bus = redis_bus_module

    yield SimpleNamespace(
        load_module=loader.load_module,
        models=models,
        state=state,
        marketing_calendar=marketing_calendar,
        campaign_log=campaign_log,
        connection=connection,
    )

    loader.restore()


@pytest.fixture
def sample_campaign_state(marketing_env: SimpleNamespace):
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    campaign = marketing_env.models.Campaign(
        campaign_id="camp_123",
        title="Launch Campaign",
        theme_slug="theme-one",
        content_snapshot={"headline": "مرحبا"},
        assets_snapshot={"hero": "/assets/hero.webp"},
        start_date=now,
        end_date=now + timedelta(days=7),
    )
    content_snapshot = marketing_env.models.ContentSnapshot(
        content_id="content_123",
        campaign_id=campaign.campaign_id,
        content_data={"body": "Launch body"},
        snapshot_date=now,
    )
    assets_snapshot = marketing_env.models.AssetSnapshot(
        asset_id="batch_123",
        campaign_id=campaign.campaign_id,
        asset_data={"hero": "/assets/hero.webp"},
        snapshot_date=now,
    )
    return marketing_env.state.MarketingState(
        current_campaign=campaign,
        content_snapshot=content_snapshot,
        assets_snapshot=assets_snapshot,
        selected_channels=["instagram"],
        selected_formats=["reel"],
        best_post_time=now + timedelta(hours=2),
        has_content_ready=True,
        has_assets_ready=True,
        product_launch_date=now - timedelta(hours=12),
    )

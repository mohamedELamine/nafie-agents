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
def visual_env() -> SimpleNamespace:
    loader = _ModuleLoader()
    visual_agent = loader.make_package("visual_production_agent", AGENT_DIR)
    loader.make_package("visual_production_agent.nodes", AGENT_DIR / "nodes", visual_agent)
    visual_db = loader.make_package("visual_production_agent.db", AGENT_DIR / "db", visual_agent)

    logging_config = types.ModuleType("visual_production_agent.logging_config")
    logging_config.get_logger = lambda name: MagicMock()
    loader.set_module("visual_production_agent.logging_config", logging_config)
    visual_agent.logging_config = logging_config

    db_module = types.ModuleType("visual_production_agent.db")
    db_module.__file__ = str(AGENT_DIR / "db" / "__init__.py")
    db_module.save_batch = MagicMock()
    db_module.save_manifest = MagicMock()
    loader.set_module("visual_production_agent.db", db_module)

    connection_module = types.ModuleType("visual_production_agent.db.connection")
    connection_module.__file__ = str(AGENT_DIR / "db" / "connection.py")
    connection_module.get_conn = lambda: None
    loader.set_module("visual_production_agent.db.connection", connection_module)
    db_module.connection = connection_module
    visual_agent.db = db_module

    yield SimpleNamespace(
        agent_dir=AGENT_DIR,
        load_module=loader.load_module,
        db=db_module,
        connection=connection_module,
    )

    loader.restore()


@pytest.fixture
def sample_batch_state() -> dict:
    return {
        "batch_id": "batch_123",
        "theme_slug": "theme-one",
        "version": "1.0.0",
        "owner_email": "owner@example.com",
        "processed_assets": {
            "processed": {
                "hero_image": {
                    "dimensions": {"width": 1920, "height": 1080},
                    "size_kb": 128,
                    "quality_score": 0.94,
                }
            },
            "total_size_kb": 128,
        },
        "published_assets": {
            "assets": [
                {
                    "asset_id": "asset_hero",
                    "type": "hero_image",
                    "url": "/assets/hero/asset_hero.webp",
                    "dimensions": {"width": 1920, "height": 1080},
                    "size_kb": 128,
                    "quality_score": 0.94,
                }
            ]
        },
        "assets": [
            {
                "asset_id": "asset_hero",
                "type": "hero_image",
                "url": "/assets/hero/asset_hero.webp",
                "dimensions": {"width": 1920, "height": 1080},
                "size_kb": 128,
                "quality_score": 0.94,
            }
        ],
    }

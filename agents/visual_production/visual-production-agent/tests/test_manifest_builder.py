import asyncio
import importlib.util
from datetime import datetime, timezone
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock

AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

from core.contracts import EVENT_THEME_ASSETS_READY, STREAM_ASSET_EVENTS

manifest_builder = _load_module(
    "manifest_builder_under_test",
    AGENT_ROOT / "nodes" / "manifest_builder.py",
)
ManifestBuilderNode = manifest_builder.ManifestBuilderNode


def test_manifest_builder_publishes_assets_ready_to_asset_stream():
    redis_bus = MagicMock()
    redis_bus.build_event = AsyncMock(
        return_value={"event_type": EVENT_THEME_ASSETS_READY, "data": {"theme_slug": "theme-one"}}
    )
    redis_bus.publish_stream = AsyncMock(return_value=True)

    node = ManifestBuilderNode(redis_bus)
    result = asyncio.run(
        node(
            batch_id="batch_1",
            theme_slug="theme-one",
            approved_assets={
                "processed": {
                    "hero": {
                        "dimensions": {"width": 1920, "height": 1080},
                        "size_kb": 128,
                        "quality_score": 0.92,
                    }
                }
            },
        )
    )

    assert result["event_published"] is True
    redis_bus.publish_stream.assert_awaited_once_with(
        stream_name=STREAM_ASSET_EVENTS,
        data={"event_type": EVENT_THEME_ASSETS_READY, "data": {"theme_slug": "theme-one"}},
    )


def test_manifest_builder_returns_manifest_with_required_fields():
    redis_bus = MagicMock()
    redis_bus.build_event = AsyncMock(
        return_value={"event_type": EVENT_THEME_ASSETS_READY, "data": {"theme_slug": "theme-one"}}
    )
    redis_bus.publish_stream = AsyncMock(return_value=True)

    node = ManifestBuilderNode(redis_bus)
    result = asyncio.run(
        node(
            batch_id="batch_1",
            theme_slug="theme-one",
            approved_assets={
                "assets": [
                    {
                        "asset_id": "asset_1",
                        "type": "hero_image",
                        "url": "/assets/hero/asset_1.webp",
                        "size_kb": 128,
                        "quality_score": 0.92,
                    }
                ]
            },
        )
    )

    manifest = result["manifest"]
    assert manifest["batch_id"] == "batch_1"
    assert manifest["theme_slug"] == "theme-one"
    assert manifest["status"] == "published"
    assert manifest["assets"][0]["asset_id"] == "asset_1"
    assert datetime.fromisoformat(manifest["published_at"]).tzinfo == timezone.utc


def test_manifest_builder_uses_timezone_aware_published_at():
    redis_bus = MagicMock()
    redis_bus.build_event = AsyncMock(
        return_value={"event_type": EVENT_THEME_ASSETS_READY, "data": {"theme_slug": "theme-one"}}
    )
    redis_bus.publish_stream = AsyncMock(return_value=True)

    node = ManifestBuilderNode(redis_bus)
    result = asyncio.run(
        node(
            batch_id="batch_1",
            theme_slug="theme-one",
            approved_assets={"assets": []},
        )
    )

    published_at = result["manifest"]["published_at"]
    assert datetime.fromisoformat(published_at).tzinfo == timezone.utc

from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys

import pytest

from core.contracts import (
    EVENT_ANALYTICS_SIGNAL,
    EVENT_CAMPAIGN_LAUNCHED,
    EVENT_CONTENT_READY,
    EVENT_NEW_PRODUCT_LIVE,
    STREAM_ASSET_EVENTS,
    STREAM_CONTENT_EVENTS,
    STREAM_MARKETING_EVENTS,
    STREAM_PRODUCT_EVENTS,
    build_ecosystem_event,
)

pytestmark = pytest.mark.integration

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
VISUAL_ROOT = PROJECT_ROOT / "agents" / "visual_production" / "visual-production-agent"


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrefixedStreamAdapter:
    def __init__(self, redis_bus):
        self.redis_bus = redis_bus
        self._seen: dict[str, set[str]] = {}

    def build_event(self, event_type: str, campaign_id: str, data: dict, theme_slug: str | None = None):
        return build_ecosystem_event(
            event_type=event_type,
            data={"campaign_id": campaign_id, **data, **({"theme_slug": theme_slug} if theme_slug else {})},
            source="marketing_agent",
        )

    def publish_stream(self, stream: str, message: dict):
        return self.redis_bus.publish_stream(stream, message)

    def ensure_consumer_group(self, stream: str, consumer_group: str) -> None:
        return None

    def read_group(self, stream: str, *args):
        seen = self._seen.setdefault(stream, set())
        unread = []
        for message in self.redis_bus.read_stream(stream):
            message_id = message["__message_id"]
            if message_id in seen:
                continue
            seen.add(message_id)
            unread.append(dict(message))
        return unread

    def ack(self, stream: str, message_id: str) -> None:
        return None


class VisualRedisAdapter:
    def __init__(self, redis_bus):
        self.redis_bus = redis_bus

    async def build_event(
        self,
        event_type: str,
        data: dict,
        source: str = "visual_production_agent",
        correlation_id: str | None = None,
    ) -> dict:
        return build_ecosystem_event(
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
        )

    async def publish_stream(self, stream_name: str, data: dict):
        return self.redis_bus.publish_stream(stream_name, data)


def test_visual_assets_flow_into_marketing_and_analytics(redis_bus, db_conn):
    from agents.marketing import agent as marketing_entry
    from agents.analytics import agent as analytics_entry

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    manifest_builder = _load_module(
        "visual_manifest_builder_integration",
        VISUAL_ROOT / "nodes" / "manifest_builder.py",
    )
    visual_stream_bus = VisualRedisAdapter(redis_bus)
    manifest_node = manifest_builder.ManifestBuilderNode(redis_bus=visual_stream_bus)

    marketing_agent = marketing_entry.MarketingAgent()
    marketing_agent.bus = redis_bus
    marketing_agent._stream_bus = PrefixedStreamAdapter(redis_bus)

    analytics_agent = analytics_entry.AnalyticsAgent()
    analytics_agent.bus = redis_bus
    analytics_agent._stream_bus = PrefixedStreamAdapter(redis_bus)

    redis_bus.publish_trigger(
        STREAM_PRODUCT_EVENTS,
        {"event_type": EVENT_NEW_PRODUCT_LIVE, "data": {"theme_slug": "theme-one", "version": "1.0.0"}},
    )
    redis_bus.publish_trigger(
        STREAM_CONTENT_EVENTS,
        {"event_type": EVENT_CONTENT_READY, "data": {"theme_slug": "theme-one", "content_id": "content_123"}},
    )
    asyncio.run(
        manifest_node(
            batch_id="batch_123",
            theme_slug="theme-one",
            approved_assets={
                "assets": [
                    {
                        "asset_id": "asset_hero",
                        "type": "hero_image",
                        "url": "/assets/hero/asset_hero.webp",
                        "size_kb": 128,
                        "quality_score": 0.92,
                    }
                ]
            },
        )
    )

    asyncio.run(marketing_agent._poll_stream(STREAM_PRODUCT_EVENTS))
    asyncio.run(marketing_agent._poll_stream(STREAM_ASSET_EVENTS))
    asyncio.run(marketing_agent._poll_stream(STREAM_CONTENT_EVENTS))

    marketing_events = redis_bus.read_stream(STREAM_MARKETING_EVENTS)
    launched_events = [event for event in marketing_events if event.get("event_type") == EVENT_CAMPAIGN_LAUNCHED]
    assert launched_events
    assert launched_events[-1]["data"]["theme_slug"] == "theme-one"
    assert launched_events[-1]["data"]["asset_batch_id"] == "batch_123"

    for event in analytics_agent._stream_bus.read_group(STREAM_MARKETING_EVENTS, "analytics-agent", "analytics-test"):
        asyncio.run(analytics_agent._publish_signal_from_marketing(event))

    analytics_signals = redis_bus.read_stream("analytics:signals")
    assert analytics_signals
    assert analytics_signals[-1]["event_type"] == EVENT_ANALYTICS_SIGNAL
    assert analytics_signals[-1]["theme_slug"] == "theme-one"

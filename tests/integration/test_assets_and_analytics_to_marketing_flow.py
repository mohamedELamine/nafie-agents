from __future__ import annotations

import asyncio

import pytest

from core.state import AgentName, EventType

pytestmark = pytest.mark.integration


def test_visual_ready_event_reaches_marketing_agent(redis_bus, db_conn, monkeypatch):
    from agents.marketing import agent as marketing_entry

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    def fake_run_marketing_pipeline(state):
        return {
            "success": True,
            "campaign_id": "camp_assets_123",
            "theme_slug": "theme-one",
        }

    monkeypatch.setattr(
        marketing_entry,
        "run_marketing_pipeline",
        fake_run_marketing_pipeline,
    )

    agent = marketing_entry.MarketingAgent()
    agent.bus = redis_bus

    redis_bus.publish_trigger(
        "asset-events",
        {
            "event_type": "THEME_ASSETS_READY",
            "data": {"theme_slug": "theme-one", "batch_id": "batch_123"},
        },
    )

    event = redis_bus.build_business_event(
        event_type=EventType.VISUAL_READY,
        payload={},
        source=AgentName.VISUAL_PRODUCTION,
    )

    asyncio.run(agent.run(event))

    published = redis_bus.read_stream("marketing-events")
    assert published
    assert published[-1]["event_type"] == EventType.CAMPAIGN_SENT.value
    assert published[-1]["payload"]["campaign_id"] == "camp_assets_123"


def test_marketing_event_reaches_analytics_agent(redis_bus, db_conn, monkeypatch):
    from agents.analytics import agent as analytics_entry

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    class FakeImmediateEvaluator:
        def evaluate(self, event):
            redis_bus.publish_stream(
                "analytics:signals",
                {
                    "event_type": "ANALYTICS_SIGNAL",
                    "theme_slug": event["payload"].get("theme_slug"),
                    "source_event": event["event_type"].value,
                },
            )

    monkeypatch.setattr(
        analytics_entry,
        "ImmediateEvaluator",
        FakeImmediateEvaluator,
    )

    agent = analytics_entry.AnalyticsAgent()
    agent.bus = redis_bus

    redis_bus.publish_trigger(
        "marketing-events",
        {
            "event_type": "CAMPAIGN_SENT",
            "data": {"theme_slug": "theme-one", "campaign_id": "camp_analytics_123"},
        },
    )

    event = redis_bus.build_business_event(
        event_type=EventType.CAMPAIGN_SENT,
        payload={"theme_slug": "theme-one", "campaign_id": "camp_analytics_123"},
        source=AgentName.MARKETING,
    )

    asyncio.run(agent.run(event))

    published = redis_bus.read_stream("analytics:signals")
    assert published
    assert published[-1]["event_type"] == "ANALYTICS_SIGNAL"
    assert published[-1]["theme_slug"] == "theme-one"

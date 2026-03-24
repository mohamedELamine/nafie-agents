from __future__ import annotations

import asyncio

import pytest

from core.state import AgentName, EventType

pytestmark = pytest.mark.integration


def test_content_ready_event_reaches_marketing_agent(redis_bus, db_conn, monkeypatch):
    from agents.marketing import agent as marketing_entry

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    def fake_run_marketing_pipeline(state):
        assert state.readiness_status == "pending"
        return {
            "success": True,
            "campaign_id": "camp_123",
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
        "content-events",
        {
            "event_type": "CONTENT_READY",
            "data": {"theme_slug": "theme-one", "content_id": "content_123"},
        },
    )

    event = redis_bus.build_business_event(
        event_type=EventType.CONTENT_READY,
        payload={},
        source=AgentName.CONTENT,
    )

    asyncio.run(agent.run(event))

    published = redis_bus.read_stream("marketing-events")
    assert published
    assert published[-1]["event_type"] == EventType.CAMPAIGN_SENT.value
    assert published[-1]["payload"]["campaign_id"] == "camp_123"

from __future__ import annotations

import asyncio

import pytest

from core.state import AgentName, EventType

pytestmark = pytest.mark.integration


def test_platform_trigger_reaches_content_agent(redis_bus, db_conn, monkeypatch):
    from agents.content import agent as content_entry

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT 1")

    def fake_run_content_pipeline(request, **services):
        assert request.theme_slug == "theme-one"
        assert request.requester == "platform_agent"
        return {
            "status": "completed",
            "content_id": "content_123",
            "theme_slug": request.theme_slug,
            "request_id": request.request_id,
        }

    monkeypatch.setattr(
        content_entry,
        "run_content_pipeline",
        fake_run_content_pipeline,
    )

    agent = content_entry.ContentAgent()
    agent.bus = redis_bus

    redis_bus.publish_trigger(
        "product-events",
        {
            "event_type": "NEW_PRODUCT_LIVE",
            "data": {"theme_slug": "theme-one", "version": "1.0.0"},
        },
    )

    event = redis_bus.build_business_event(
        event_type=EventType.CONTENT_REQUESTED,
        payload={
            "request_id": "req_123",
            "trigger": "event",
            "requester": "platform_agent",
            "content_type": "email_launch",
            "content_category": "commercial",
            "theme_slug": "theme-one",
            "theme_contract": {"slug": "theme-one"},
            "raw_context": {"theme_slug": "theme-one"},
            "target_agent": "marketing_agent",
            "correlation_id": "corr_123",
            "priority": "normal",
            "output_mode": "single",
            "variant_count": 1,
            "evidence_contract": None,
            "created_at": "2026-03-24T12:00:00+00:00",
        },
        source=AgentName.PLATFORM,
    )

    asyncio.run(agent.run(event))

    published = redis_bus.read_stream("content-events")
    assert published
    assert published[-1]["event_type"] == EventType.CONTENT_READY.value
    assert published[-1]["payload"]["theme_slug"] == "theme-one"

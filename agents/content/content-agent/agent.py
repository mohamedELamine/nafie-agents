"""
Content Agent — Graph Builder
يبني LangGraph StateGraph لوكيل المحتوى.
المرجع: spec.md § ٩ (خريطة Nodes)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional

# Add parent directories to path for core imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from core.base_agent import BaseAgent
from core.state import AgentName, BusinessEvent, EventType

from langgraph.graph import END, StateGraph

from db.content_registry import ContentRegistry
from models import ContentRequest
from nodes import (
    make_category_router_node,
    make_content_dispatcher_node,
    make_content_error_node,
    make_content_generator_node,
    make_content_planner_node,
    make_content_recorder_node,
    make_content_validator_node,
    make_context_enricher_node,
    make_evidence_gate_node,
    make_fact_normalizer_node,
    make_idempotency_check_node,
    make_registry_updater_node,
    make_request_receiver_node,
    make_review_gate_node,
    make_template_selector_node,
    route_after_evidence,
    route_after_idempotency,
    route_after_review,
    route_after_validation,
)
from services.claude_client import ClaudeContentClient
from services.redis_bus import RedisBus
from services.resend_client import ContentResendClient
from state import ContentState, make_initial_state

logger = logging.getLogger("content_agent.agent")


def build_content_graph(
    registry:     Optional[ContentRegistry]      = None,
    claude:       Optional[ClaudeContentClient]  = None,
    redis_bus:    Optional[RedisBus]             = None,
    resend:       Optional[ContentResendClient]  = None,
):
    """
    يبني الـ graph الكامل مع dependency injection.

    الترتيب:
    request_receiver → idempotency_check → category_router → content_planner
    → context_enricher → evidence_gate → fact_normalizer → template_selector
    → content_generator → content_validator → review_gate
    → content_dispatcher → registry_updater → content_recorder → END
    """
    # ── Services Init ─────────────────────────────────────────────
    _registry  = registry  or ContentRegistry()
    _claude    = claude    or ClaudeContentClient()
    _redis     = redis_bus or RedisBus()
    _resend    = resend    or ContentResendClient()

    # ── Graph ─────────────────────────────────────────────────────
    g = StateGraph(ContentState)

    # ── Nodes ─────────────────────────────────────────────────────
    g.add_node("request_receiver",    make_request_receiver_node())
    g.add_node("idempotency_check",   make_idempotency_check_node())
    g.add_node("category_router",     make_category_router_node())
    g.add_node("content_planner",     make_content_planner_node())
    g.add_node("context_enricher",    make_context_enricher_node(_registry))
    g.add_node("evidence_gate",       make_evidence_gate_node(_redis))
    g.add_node("fact_normalizer",     make_fact_normalizer_node(_claude))
    g.add_node("template_selector",   make_template_selector_node())
    g.add_node("content_generator",   make_content_generator_node(_claude))
    g.add_node("content_validator",   make_content_validator_node(_claude))
    g.add_node("review_gate",         make_review_gate_node(_registry, _resend))
    g.add_node("content_dispatcher",  make_content_dispatcher_node(_redis))
    g.add_node("registry_updater",    make_registry_updater_node(_registry))
    g.add_node("content_recorder",    make_content_recorder_node(_registry))
    g.add_node("content_error",       make_content_error_node(_registry))

    # ── Entry Point ───────────────────────────────────────────────
    g.set_entry_point("request_receiver")

    # ── Edges ─────────────────────────────────────────────────────
    g.add_edge("request_receiver",  "idempotency_check")
    g.add_conditional_edges(
        "idempotency_check",
        route_after_idempotency,
        {"END": END, "category_router": "category_router"},
    )
    g.add_edge("category_router",   "content_planner")
    g.add_edge("content_planner",   "context_enricher")
    g.add_edge("context_enricher",  "evidence_gate")
    g.add_conditional_edges(
        "evidence_gate",
        route_after_evidence,
        {"END": END, "fact_normalizer": "fact_normalizer"},
    )
    g.add_edge("fact_normalizer",   "template_selector")
    g.add_edge("template_selector", "content_generator")
    g.add_conditional_edges(
        "content_validator",
        route_after_validation,
        {
            "content_generator": "content_generator",   # إعادة توليد
            "content_error":     "content_error",
            "review_gate":       "review_gate",
        },
    )
    g.add_edge("content_generator",  "content_validator")
    g.add_conditional_edges(
        "review_gate",
        route_after_review,
        {"END": END, "content_dispatcher": "content_dispatcher"},
    )
    g.add_edge("content_dispatcher", "registry_updater")
    g.add_edge("registry_updater",   "content_recorder")
    g.add_edge("content_recorder",   END)
    g.add_edge("content_error",      END)

    return g.compile()


def run_content_pipeline(request: ContentRequest, **services) -> dict:
    """يُشغّل الـ pipeline الكامل لطلب محتوى."""
    graph        = build_content_graph(**services)
    initial_state = make_initial_state(request)

    logger.info(
        "content_pipeline.start req=%s type=%s",
        request.request_id, request.content_type,
    )

    result = graph.invoke(initial_state)

    logger.info(
        "content_pipeline.end req=%s status=%s",
        request.request_id, result.get("status"),
    )
    return result


# ── BaseAgent subclass ─────────────────────────────────────────────

class ContentAgent(BaseAgent):
    """Content agent — inherits BaseAgent for Redis, heartbeats, and supervision."""

    agent_name = AgentName.CONTENT

    async def setup_handlers(self) -> None:
        await self.bus.subscribe(
            EventType.CONTENT_REQUESTED,
            self.run,
        )

    async def run(self, event: BusinessEvent) -> None:
        try:
            request = ContentRequest(**event["payload"])
            result = run_content_pipeline(request)
            if result.get("status") == "completed":
                await self.emit(
                    EventType.CONTENT_READY,
                    result,
                    trace_id=event.get("trace_id"),
                )
        except Exception as e:
            await self.emit_error(str(e), trace_id=event.get("trace_id"))


if __name__ == "__main__":
    agent = ContentAgent()
    asyncio.run(agent.start())

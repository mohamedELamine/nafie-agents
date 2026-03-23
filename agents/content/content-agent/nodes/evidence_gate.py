"""
Node: EVIDENCE_GATE
يتحقق من EvidenceContract لـ KNOWLEDGE_ARTICLE.
المرجع: spec.md § ١٦
"""
from __future__ import annotations
import logging
import json
from state import ContentState
from models import ContentType

logger = logging.getLogger("content_agent.nodes.evidence_gate")


def make_evidence_gate_node(redis_bus):
    def evidence_gate_node(state: ContentState) -> dict:
        request = state["request"]

        # لا يُطبَّق على أنواع أخرى
        if ContentType(request.content_type) != ContentType.KNOWLEDGE_ARTICLE:
            return {"evidence_verified": True}

        evidence = request.evidence_contract

        if not evidence:
            logger.warning("evidence_gate.no_evidence req=%s", request.request_id)
            # أُشعر وكيل الدعم
            _notify_support(redis_bus, request, "لا يوجد EvidenceContract")
            return {
                "status":      "draft_only",
                "error_code":  "CON_KNOWLEDGE_NO_EVIDENCE",
                "error_detail": "KNOWLEDGE_ARTICLE بلا EvidenceContract",
            }

        if not evidence.confirmed_resolution_steps:
            logger.warning("evidence_gate.incomplete req=%s", request.request_id)
            _notify_support(redis_bus, request, "EvidenceContract ناقص — خطوات الحل غائبة")
            return {
                "status":      "draft_only",
                "error_code":  "CON_KNOWLEDGE_INCOMPLETE_EVIDENCE",
                "error_detail": "EvidenceContract ناقص",
            }

        logger.info("evidence_gate.verified req=%s", request.request_id)
        return {"evidence_verified": True}

    return evidence_gate_node


def route_after_evidence(state: ContentState) -> str:
    if state.get("status") in ("draft_only", "failed"):
        return "END"
    return "fact_normalizer"


def _notify_support(redis_bus, request, reason: str) -> None:
    try:
        event = redis_bus.build_event(
            event_type     = "KNOWLEDGE_DRAFT_REQUESTED",
            data           = {
                "theme_slug": request.theme_slug,
                "issue":      request.raw_context.get("issue", ""),
                "reason":     reason,
            },
            correlation_id = request.correlation_id,
        )
        redis_bus.publish("support-events", event)
    except Exception as exc:
        logger.error("evidence_gate.notify_support_failed err=%s", exc)

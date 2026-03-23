"""
Node: REVIEW_GATE
يُطبّق REVIEW_POLICY ويقرر: auto أو human_review.
المرجع: spec.md § ١٥
"""
from __future__ import annotations
import logging
import uuid
from state import ContentState
from models import ContentStatus, ReviewPolicy

logger = logging.getLogger("content_agent.nodes.review_gate")


def make_review_gate_node(registry, resend):
    def review_gate_node(state: ContentState) -> dict:
        piece  = state.get("content_piece")
        plan   = state.get("content_plan")
        request = state["request"]

        if not piece or not plan:
            return {
                "status":      "failed",
                "error_code":  "CON_GENERATION_FAILED",
                "error_detail": "piece أو plan غائب في review_gate",
            }

        policy = plan.review_policy
        score  = piece.validation_score
        requires_review = _should_require_review(policy, score)

        if requires_review:
            review_key = f"review:{request.request_id}:{str(uuid.uuid4())[:8]}"
            piece.status = ContentStatus.AWAITING_REVIEW

            # حفظ في طابور المراجعة
            registry.queue_for_human_review(
                piece          = piece,
                review_key     = review_key,
                requester      = request.requester,
                correlation_id = request.correlation_id,
            )

            # إشعار صاحب المشروع
            resend.send_review_request(
                content_type     = request.content_type.value if hasattr(request.content_type, 'value') else str(request.content_type),
                theme_slug       = request.theme_slug or "عام",
                validation_score = score,
                body_preview     = str(piece.body)[:300],
                review_key       = review_key,
                requester        = request.requester,
            )

            logger.info(
                "review_gate.human_required req=%s key=%s policy=%s score=%.2f",
                request.request_id, review_key, policy.value, score,
            )
            return {
                "content_piece":       piece,
                "awaiting_human_review": True,
                "status":              "awaiting_review",
            }

        logger.info(
            "review_gate.auto req=%s policy=%s score=%.2f",
            request.request_id, policy.value, score,
        )
        return {
            "content_piece":       piece,
            "awaiting_human_review": False,
            "status":              "auto_approved",
        }

    return review_gate_node


def route_after_review(state: ContentState) -> str:
    if state.get("awaiting_human_review"):
        return "END"  # يتوقف حتى قرار بشري عبر API
    return "content_dispatcher"


def _should_require_review(policy: ReviewPolicy, score: float) -> bool:
    if policy == ReviewPolicy.AUTO_PUBLISH:
        return False
    if policy == ReviewPolicy.AUTO_IF_SCORE:
        return score < 0.80
    if policy == ReviewPolicy.HUMAN_REVIEW_REQUIRED:
        return True
    if policy == ReviewPolicy.HUMAN_REVIEW_OPTIONAL:
        return False
    if policy == ReviewPolicy.HUMAN_IF_LOW_SCORE:
        return score < 0.75
    return False

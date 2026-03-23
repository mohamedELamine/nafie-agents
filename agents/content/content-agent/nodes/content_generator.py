"""
Node: CONTENT_GENERATOR
يولّد المحتوى بـ Claude مع Brand Constitution + FactSheet.
المرجع: spec.md § ١٣، ١٧
"""
from __future__ import annotations
import logging
from state import ContentState
from models import VARIANT_SUPPORT, ContentType

logger = logging.getLogger("content_agent.nodes.content_generator")


def make_content_generator_node(claude_client):
    def content_generator_node(state: ContentState) -> dict:
        request   = state["request"]
        plan      = state.get("content_plan")
        fact_sheet = state.get("fact_sheet")
        template  = state.get("selected_template")

        if not plan or not fact_sheet:
            return {
                "status":      "failed",
                "error_code":  "CON_GENERATION_FAILED",
                "error_detail": "ContentPlan أو FactSheet غائب",
            }

        content_type = ContentType(request.content_type)
        use_variants = (
            plan.output_mode == "variants"
            and plan.variant_count > 1
            and VARIANT_SUPPORT.get(content_type, False)
        )

        try:
            if use_variants:
                pieces = claude_client.generate_variants(request, plan, fact_sheet, template)
            else:
                piece  = claude_client.generate_single(request, plan, fact_sheet, template)
                pieces = [piece]
        except Exception as exc:
            logger.error("content_generator.failed req=%s err=%s", request.request_id, exc)
            return {
                "status":      "failed",
                "error_code":  "CON_GENERATION_FAILED",
                "error_detail": str(exc),
            }

        logger.info(
            "content_generator.done req=%s pieces=%d",
            request.request_id, len(pieces),
        )
        return {
            "content_piece":  pieces[0],
            "content_pieces": pieces,
            "status":         "generated",
        }

    return content_generator_node

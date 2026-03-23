"""
Node: FACT_NORMALIZER
يُنتج FactSheet قبل التوليد — حارس الحقائق.
المرجع: spec.md § ٨
"""
from __future__ import annotations
import logging
from state import ContentState
from models import BRAND_CONSTITUTION_VERSION

logger = logging.getLogger("content_agent.nodes.fact_normalizer")


def make_fact_normalizer_node(claude_client):
    def fact_normalizer_node(state: ContentState) -> dict:
        bundle   = state.get("context_bundle")
        plan     = state.get("content_plan")
        request  = state["request"]

        if not bundle:
            return {
                "status":      "failed",
                "error_code":  "CON_CONTEXT_BUILD_FAILED",
                "error_detail": "ContextBundle غائب عند FACT_NORMALIZER",
            }

        bundle_summary = f"""
الحقائق الموثوقة من THEME_CONTRACT:
{bundle.theme_facts}

ما يُسمح بادعائه:
{bundle.allowed_claims}

ما يُمنع ادعاؤه:
{bundle.forbidden_claims}

بيانات الإطلاق/التحديث:
{bundle.release_metadata}

قيود معروفة:
{bundle.known_constraints}
"""
        try:
            fact_sheet = claude_client.normalize_facts(
                context_bundle_summary = bundle_summary,
                constitution_version   = BRAND_CONSTITUTION_VERSION,
                template_version       = plan.template_id if plan else "default",
            )
        except Exception as exc:
            logger.error("fact_normalizer.failed req=%s err=%s", request.request_id, exc)
            return {
                "status":      "failed",
                "error_code":  "CON_FACT_NORMALIZE_FAILED",
                "error_detail": str(exc),
            }

        # ربط الـ fact_sheet بالـ plan
        if plan:
            plan.fact_sheet   = fact_sheet
            plan.key_messages = fact_sheet.verified_facts[:3]

        logger.info(
            "fact_normalizer.done req=%s facts=%d inferences=%d",
            request.request_id,
            len(fact_sheet.verified_facts),
            len(fact_sheet.allowed_inferences),
        )
        return {"fact_sheet": fact_sheet, "content_plan": plan}

    return fact_normalizer_node

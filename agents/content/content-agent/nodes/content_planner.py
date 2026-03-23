"""
Node: CONTENT_PLANNER
يبني ContentPlan من ContentRequest.
المرجع: spec.md § ١٢
"""
from __future__ import annotations
import logging
from state import ContentState
from models import (
    CONTENT_TYPE_SPECS, REVIEW_POLICY_MAP,
    ContentPlan, ContentType,
    parse_word_budget,
)

logger = logging.getLogger("content_agent.nodes.content_planner")

CHANNEL_MAP = {
    ContentType.EMAIL_UPDATE:         "بريد تقني",
    ContentType.EMAIL_LAUNCH:         "بريد تسويقي",
    ContentType.EMAIL_CAMPAIGN:       "بريد تسويقي",
    ContentType.PRODUCT_PAGE_SECTION: "صفحة منتج",
    ContentType.PRODUCT_PAGE_FULL:    "صفحة منتج",
    ContentType.KNOWLEDGE_ARTICLE:    "مقالة دعم",
    ContentType.MARKETING_COPY:       "منشور اجتماعي",
    ContentType.SOCIAL_CAPTION:       "منشور اجتماعي",
}

TONE_MAP = {
    "بريد تقني":       "رسمي موجز",
    "بريد تسويقي":     "ودود محفّز",
    "صفحة منتج":       "مقنع صادق",
    "مقالة دعم":       "تعليمي صبور",
    "منشور اجتماعي":   "خفيف مباشر",
}


def make_content_planner_node():
    def content_planner_node(state: ContentState) -> dict:
        request      = state["request"]
        content_type = ContentType(request.content_type)
        spec         = CONTENT_TYPE_SPECS.get(content_type, {})

        channel_style = CHANNEL_MAP.get(content_type, "عام")
        tone          = TONE_MAP.get(channel_style, "مهني")

        plan = ContentPlan(
            request_id       = request.request_id,
            content_type     = content_type,
            content_category = request.content_category,
            tone             = tone,
            channel_style    = channel_style,
            structure        = spec.get("الأقسام", []),
            word_budget      = parse_word_budget(spec.get("الحد", "150")),
            key_messages     = [],
            context_bundle   = None,
            fact_sheet       = None,
            template_id      = _select_template_id(request),
            review_policy    = REVIEW_POLICY_MAP[content_type],
            output_mode      = request.output_mode,
            variant_count    = request.variant_count,
        )

        logger.info(
            "content_planner req=%s type=%s tone=%s budget=%d",
            request.request_id, content_type.value, tone, plan.word_budget,
        )
        return {"content_plan": plan}

    return content_planner_node


def _select_template_id(request) -> str:
    type_to_template = {
        "email_update":         "email_update_standard",
        "email_launch":         "email_launch_standard",
        "email_campaign":       "email_campaign_standard",
        "product_page_full":    "product_page_full_standard",
        "knowledge_article":    "knowledge_article_standard",
        "marketing_copy":       "marketing_copy_standard",
        "social_caption":       "social_caption_standard",
        "product_page_section": "product_page_section_standard",
    }
    return type_to_template.get(str(request.content_type).replace("ContentType.", ""), "default")

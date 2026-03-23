"""
Node: TEMPLATE_SELECTOR
يختار ContentTemplate المناسب للطلب.
المرجع: spec.md § ٥
"""
from __future__ import annotations
import logging
from state import ContentState
from models import (
    ContentCategory, ContentTemplate, ContentType,
    REVIEW_POLICY_MAP, VARIANT_SUPPORT, CONTENT_TYPE_SPECS, parse_word_budget,
)

logger = logging.getLogger("content_agent.nodes.template_selector")


def make_template_selector_node():
    def template_selector_node(state: ContentState) -> dict:
        request      = state["request"]
        plan         = state.get("content_plan")
        content_type = ContentType(request.content_type)

        template = _build_default_template(content_type)

        if plan:
            plan.template_id = template.template_id

        logger.info(
            "template_selector req=%s template=%s",
            request.request_id, template.template_id,
        )
        return {"selected_template": template, "content_plan": plan}

    return template_selector_node


def _build_default_template(content_type: ContentType) -> ContentTemplate:
    spec    = CONTENT_TYPE_SPECS.get(content_type, {})
    channel_map = {
        ContentType.EMAIL_UPDATE:         "بريد تقني",
        ContentType.EMAIL_LAUNCH:         "بريد تسويقي",
        ContentType.EMAIL_CAMPAIGN:       "بريد تسويقي",
        ContentType.PRODUCT_PAGE_SECTION: "صفحة منتج",
        ContentType.PRODUCT_PAGE_FULL:    "صفحة منتج",
        ContentType.KNOWLEDGE_ARTICLE:    "مقالة دعم",
        ContentType.MARKETING_COPY:       "منشور اجتماعي",
        ContentType.SOCIAL_CAPTION:       "منشور اجتماعي",
    }
    tone_map = {
        "بريد تقني":     "رسمي موجز",
        "بريد تسويقي":   "ودود محفّز",
        "صفحة منتج":     "مقنع صادق",
        "مقالة دعم":     "تعليمي صبور",
        "منشور اجتماعي": "خفيف مباشر",
    }
    channel = channel_map.get(content_type, "عام")

    return ContentTemplate(
        template_id       = f"{content_type.value}_standard",
        template_version  = "1.0",
        content_type      = content_type,
        content_category  = ContentCategory.COMMERCIAL,
        name_ar           = f"قالب {content_type.value}",
        structure         = spec.get("الأقسام", []),
        tone              = tone_map.get(channel, "مهني"),
        channel_style     = channel,
        word_budget       = parse_word_budget(spec.get("الحد", "150")),
        review_policy     = REVIEW_POLICY_MAP[content_type],
        supports_variants = VARIANT_SUPPORT.get(content_type, False),
        example           = None,
    )

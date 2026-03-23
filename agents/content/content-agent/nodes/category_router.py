"""
Node: CATEGORY_ROUTER
يحدد الفئة التشغيلية من ContentType.
المرجع: spec.md § ٦
"""
from __future__ import annotations
import logging
from state import ContentState
from models import CONTENT_CATEGORY_MAP, ContentType

logger = logging.getLogger("content_agent.nodes.category_router")


def make_category_router_node():
    def category_router_node(state: ContentState) -> dict:
        request  = state["request"]
        category = CONTENT_CATEGORY_MAP.get(ContentType(request.content_type))

        if not category:
            return {
                "status":      "failed",
                "error_code":  "CON_UNKNOWN_CONTENT_TYPE",
                "error_detail": f"لا فئة لـ {request.content_type}",
            }

        logger.info(
            "category_router type=%s → category=%s",
            request.content_type, category.value,
        )
        # نُحدّث content_category في الـ request
        request.content_category = category
        return {"request": request}

    return category_router_node

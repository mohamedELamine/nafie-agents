"""
Node: REQUEST_RECEIVER
أول نقطة في الـ workflow — يستقبل ويتحقق من ContentRequest.
المرجع: spec.md § ٩
"""
from __future__ import annotations
import logging
from state import ContentState
from models import CONTENT_CATEGORY_MAP, ContentRequest, ContentTrigger, ContentType
from db.idempotency import check_completed

logger = logging.getLogger("content_agent.nodes.request_receiver")
NODE_NAME = "REQUEST_RECEIVER"

SUPPORTED_VERSIONS = {"1.0"}


def make_request_receiver_node():
    def request_receiver_node(state: ContentState) -> dict:
        request = state["request"]
        ikey    = state["idempotency_key"]

        # تحقق من الإصدار
        event_version = request.raw_context.get("event_version", "1.0")
        if event_version not in SUPPORTED_VERSIONS:
            logger.error("request_receiver.unsupported_version v=%s ikey=%s", event_version, ikey)
            return {
                "status":      "failed",
                "error_code":  "CON_UNKNOWN_CONTENT_TYPE",
                "error_detail": f"إصدار الحدث غير مدعوم: {event_version}",
            }

        # تحقق من نوع المحتوى
        try:
            ContentType(request.content_type)
        except ValueError:
            return {
                "status":      "failed",
                "error_code":  "CON_UNKNOWN_CONTENT_TYPE",
                "error_detail": f"نوع المحتوى غير معروف: {request.content_type}",
            }

        # تحقق من السياق المطلوب
        if not request.raw_context and not request.theme_contract:
            return {
                "status":      "failed",
                "error_code":  "CON_MISSING_CONTEXT",
                "error_detail": "لا سياق ولا theme_contract",
            }

        logger.info(
            "request_receiver.accepted req=%s type=%s trigger=%s",
            request.request_id, request.content_type, request.trigger,
        )
        return {"status": "processing"}

    return request_receiver_node

"""
Node: CONTENT_RECORDER
يحفظ ContentPiece في قاعدة البيانات ويختم الـ workflow.
المرجع: spec.md § ٩
"""
from __future__ import annotations
import logging
from state import ContentState
from db.idempotency import mark_completed, mark_failed

logger = logging.getLogger("content_agent.nodes.content_recorder")
NODE_NAME = "CONTENT_RECORDER"


def make_content_recorder_node(registry):
    def content_recorder_node(state: ContentState) -> dict:
        piece   = state.get("content_piece")
        pieces  = state.get("content_pieces", [])
        ikey    = state["idempotency_key"]
        request = state["request"]

        try:
            # حفظ كل المتغيرات
            for p in (pieces if pieces else ([piece] if piece else [])):
                registry.save_content_piece(p)

            mark_completed(
                ikey       = ikey,
                node_name  = NODE_NAME,
                content_id = piece.content_id if piece else None,
            )
            logger.info(
                "content_recorder.saved req=%s pieces=%d",
                request.request_id, len(pieces) or 1,
            )
        except Exception as exc:
            logger.error("content_recorder.failed req=%s err=%s", request.request_id, exc)
            # لا نوقف — التسليم حصل بالفعل

        return {"status": "completed"}

    return content_recorder_node


def make_content_error_node(registry):
    """يُسجّل الفشل النهائي ويُنهي الـ workflow."""
    def content_error_node(state: ContentState) -> dict:
        ikey       = state["idempotency_key"]
        error_code = state.get("error_code", "CON_MAX_REGENERATION_REACHED")
        detail     = state.get("error_detail", "تجاوز حد إعادة التوليد")
        request    = state["request"]

        mark_failed(
            ikey         = ikey,
            node_name    = "CONTENT_ERROR",
            error_code   = error_code,
            error_detail = detail,
        )

        # تسجيل في dead-letter
        logger.error(
            "content_error req=%s code=%s detail=%s",
            request.request_id, error_code, detail,
        )
        return {
            "status":      "failed",
            "error_code":  error_code,
            "error_detail": detail,
        }

    return content_error_node

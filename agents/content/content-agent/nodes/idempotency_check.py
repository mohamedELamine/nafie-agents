"""
Node: IDEMPOTENCY_CHECK
يتجاوز الطلبات المكتملة مسبقاً.
المرجع: spec.md § ٢٠
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_started
from state import ContentState

logger = logging.getLogger("content_agent.nodes.idempotency_check")
NODE_NAME = "IDEMPOTENCY_CHECK"


def make_idempotency_check_node():
    def idempotency_check_node(state: ContentState) -> dict:
        ikey = state["idempotency_key"]

        if check_completed(ikey):
            logger.info("idempotency_check.skip ikey=%s", ikey)
            return {"status": "already_completed"}

        mark_started(ikey, NODE_NAME)
        return {"status": "processing"}

    return idempotency_check_node


def route_after_idempotency(state: ContentState) -> str:
    if state.get("status") == "already_completed":
        return "END"
    return "category_router"

"""
Node: PRODUCT_CREATOR — T044
ينشئ منتج Lemon Squeezy بـ status=draft.
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from services.ls_client import LemonSqueezyClient, LemonSqueezyError
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.product_creator")
NODE_NAME = "PRODUCT_CREATOR"

def make_product_creator_node(registry: ProductRegistry, ls_client: LemonSqueezyClient):
    def product_creator_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        parsed = state.get("parsed", {})
        theme_name_ar = parsed.get("theme_name_ar", state["theme_slug"])

        try:
            created = ls_client.create_product(theme_name_ar, state["theme_slug"])
        except LemonSqueezyError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("PRODUCT_CREATOR | PLT_201 | %s", exc)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": exc.error_code,
                    "error": str(exc),
                    "logs": state.get("logs",[]) + [f"PRODUCT_CREATOR: FAILED {exc.error_code}"]}

        result = {
            **state,
            "ls_product_id": created["product_id"],
            "ls_variants": [
                {"tier": "single",    "id": created["single_variant_id"]},
                {"tier": "unlimited", "id": created["unlimited_variant_id"]},
            ],
            "logs": state.get("logs",[]) + [f"PRODUCT_CREATOR: ls_product_id={created['product_id']}"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("PRODUCT_CREATOR | DONE | product_id=%s", created["product_id"])
        return result
    return product_creator_node

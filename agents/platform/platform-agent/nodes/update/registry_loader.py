"""Node: REGISTRY_LOADER — T057 | wp_post_id من هنا فقط"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.registry_loader")
NODE_NAME = "REGISTRY_LOADER"

def make_registry_loader_node(registry: ProductRegistry):
    def registry_loader_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        theme_slug = state["theme_slug"]
        new_version = state["new_version"]
        record = registry.get(theme_slug)

        if not record:
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_701",
                    "error": f"القالب '{theme_slug}' غير موجود في Registry"}

        # تحقق من التكرار
        if record.get("current_version") == new_version:
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_702",
                    "error": f"الإصدار {new_version} مُسجَّل بالفعل"}

        result = {
            **state,
            "ls_product_id": record["ls_product_id"],
            "ls_single_variant": record.get("ls_single_variant", ""),
            "ls_unlimited_variant": record.get("ls_unlimited_variant", ""),
            "wp_post_id": record["wp_post_id"],   # من Registry فقط
            "wp_post_url": record.get("wp_post_url", ""),
            "previous_version": record.get("current_version", ""),
            "logs": state.get("logs",[]) + [f"REGISTRY_LOADER: wp_post_id={record['wp_post_id']} loaded"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("REGISTRY_LOADER | DONE | theme=%s wp=%s", theme_slug, record["wp_post_id"])
        return result
    return registry_loader_node

"""
Node: ASSET_WAITER — T043
ينتظر الأصول البصرية (screenshot مطلوب). يُعلّق الـ workflow إن لم تكن جاهزة.
Asset Timeout Policy: 4h → إشعار، 8h → إلغاء تلقائي.
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.asset_waiter")
NODE_NAME = "ASSET_WAITER"

def make_asset_waiter_node(registry: ProductRegistry, redis_bus):
    def asset_waiter_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        assets = state.get("collected_assets", {})
        # screenshot إلزامي دائماً
        if not assets.get("screenshot"):
            logger.info("ASSET_WAITER | WAITING | key=%s | screenshot missing", ikey)
            # حفظ checkpoint في Redis للاستئناف لاحقاً
            try:
                redis_bus._redis.setex(
                    f"workflow:{ikey}:checkpoint",
                    28800,  # 8 ساعات TTL
                    NODE_NAME,
                )
            except Exception as exc:
                logger.warning("ASSET_WAITER | checkpoint save failed | %s", exc)
            result = {
                **state,
                "status": PlatformStatus.WAITING_ASSETS,
                "logs": state.get("logs",[]) + ["ASSET_WAITER: WAITING for screenshot"],
            }
            # لا نستدعي mark_completed — الـ workflow سيستأنف عند استلام THEME_ASSETS_READY
            return result

        result = {
            **state,
            "logs": state.get("logs",[]) + [f"ASSET_WAITER: assets ready {list(assets.keys())}"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("ASSET_WAITER | PASS | theme=%s assets=%s", state["theme_slug"], list(assets.keys()))
        return result
    return asset_waiter_node

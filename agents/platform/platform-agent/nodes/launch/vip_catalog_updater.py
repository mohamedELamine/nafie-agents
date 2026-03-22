"""
Node: VIP_CATALOG_UPDATER — T046
يُضيف القالب الجديد لـ VIP Bundle ويُحدّث vip_registry في PostgreSQL.
VIP منتج مستقل — لا variant داخل المنتج الجديد (Constitution IX).
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.ls_client import LemonSqueezyClient
from state import LaunchState

logger = logging.getLogger("platform_agent.nodes.launch.vip_catalog_updater")
NODE_NAME = "VIP_CATALOG_UPDATER"

def make_vip_catalog_updater_node(registry: ProductRegistry, ls_client: LemonSqueezyClient):
    def vip_catalog_updater_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        theme_slug = state["theme_slug"]

        # جلب VIP product من LS
        vip = ls_client.get_vip_product()
        vip_product_id = vip["id"] if vip else None

        if vip_product_id:
            ls_client.add_theme_to_vip(vip_product_id, theme_slug)
            # تحديث vip_registry في PostgreSQL
            try:
                with registry.db.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE vip_registry
                        SET theme_slugs = array_append(theme_slugs, %s),
                            last_updated_at = NOW()
                        WHERE ls_product_id = %s
                        """,
                        (theme_slug, vip_product_id),
                    )
                registry.db.commit()
            except Exception as exc:
                logger.warning("VIP_CATALOG_UPDATER | DB update failed | %s", exc)
                registry.db.rollback()

        result = {
            **state,
            "vip_product_id": vip_product_id,
            "logs": state.get("logs",[]) + [f"VIP_CATALOG_UPDATER: vip_id={vip_product_id} added={theme_slug}"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("VIP_CATALOG_UPDATER | DONE | theme=%s vip_id=%s", theme_slug, vip_product_id)
        return result
    return vip_catalog_updater_node

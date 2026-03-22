"""Node: ELIGIBILITY_FILTER — T060 | من يستحق إيميل التحديث؟"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.ls_client import LemonSqueezyClient
from state import UpdateState

logger = logging.getLogger("platform_agent.nodes.update.eligibility_filter")
NODE_NAME = "ELIGIBILITY_FILTER"

def make_eligibility_filter_node(registry: ProductRegistry, ls_client: LemonSqueezyClient):
    def eligibility_filter_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        ls_product_id = state["ls_product_id"]
        new_version = state["new_version"]
        theme_slug = state["theme_slug"]
        changelog = state.get("changelog", {})
        is_security = changelog.get("is_security", False)

        all_licenses = ls_client.get_active_licenses(ls_product_id)
        eligible = []
        for buyer in all_licenses:
            email = buyer.get("email", "")
            if not email:
                continue
            # تحقق من notification_log — هل أُرسل هذا الإيميل من قبل؟
            if _already_notified(registry.db, email, theme_slug, new_version):
                continue
            # التحديثات الأمنية تتجاوز opt_in
            if is_security:
                eligible.append(buyer)
                continue
            # شروط عادية
            if buyer.get("status") == "active":
                eligible.append(buyer)

        result = {
            **state,
            "eligible_buyers": eligible,
            "logs": state.get("logs",[]) + [
                f"ELIGIBILITY_FILTER: {len(eligible)}/{len(all_licenses)} eligible"
            ],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("ELIGIBILITY_FILTER | eligible=%s total=%s", len(eligible), len(all_licenses))
        return result
    return eligibility_filter_node

def _already_notified(db_conn, email: str, theme_slug: str, version: str) -> bool:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM notification_log WHERE buyer_email=%s AND theme_slug=%s AND version=%s LIMIT 1",
            (email, theme_slug, version),
        )
        return cur.fetchone() is not None

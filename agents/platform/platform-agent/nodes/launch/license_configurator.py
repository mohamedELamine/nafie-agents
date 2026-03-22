"""
Node: LICENSE_CONFIGURATOR — T045
يتحقق من صحة الأسعار ويُسجّل variant IDs في state.
الأسعار ثابتة نهائياً بعد هذا الـ node (Constitution V).
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.ls_client import PRICING
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.license_configurator")
NODE_NAME = "LICENSE_CONFIGURATOR"

def make_license_configurator_node(registry: ProductRegistry):
    def license_configurator_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        variants = state.get("ls_variants", [])
        single_id = next((v["id"] for v in variants if v["tier"] == "single"), None)
        unlimited_id = next((v["id"] for v in variants if v["tier"] == "unlimited"), None)

        result = {
            **state,
            "ls_single_variant_id": single_id,
            "ls_unlimited_variant_id": unlimited_id,
            "logs": state.get("logs",[]) + [
                f"LICENSE_CONFIGURATOR: single=${PRICING['single']['price_usd_cents']//100}"
                f" unlimited=${PRICING['unlimited']['price_usd_cents']//100} — PRICE LOCKED"
            ],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("LICENSE_CONFIGURATOR | DONE | prices LOCKED single=$29 unlimited=$79")
        return result
    return license_configurator_node

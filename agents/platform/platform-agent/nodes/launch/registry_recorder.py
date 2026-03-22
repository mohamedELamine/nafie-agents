"""
Node: REGISTRY_RECORDER — T051
يحفظ ThemeRecord في theme_registry مع Provenance كامل.
wp_post_id يُخزَّن هنا — مصدر الحقيقة الوحيد.
المرجع: spec.md § ٤ | tasks/phase3 § T051
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry, RegistryError
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.registry_recorder")
NODE_NAME = "REGISTRY_RECORDER"

def make_registry_recorder_node(registry: ProductRegistry):
    def registry_recorder_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        parsed = state.get("parsed", {})
        theme_slug = state["theme_slug"]

        record = {
            "theme_slug": theme_slug,
            "theme_name_ar": parsed.get("theme_name_ar", theme_slug),
            "domain": parsed.get("domain", "general"),
            "cluster": parsed.get("cluster", "ecommerce"),
            "woocommerce_enabled": parsed.get("woocommerce_enabled", False),
            "cod_enabled": parsed.get("cod_enabled", False),
            # WordPress — المصدر الوحيد لـ wp_post_id
            "wp_post_id": state["wp_post_id"],
            "wp_post_url": state.get("wp_post_url", ""),
            # Lemon Squeezy
            "ls_product_id": state["ls_product_id"],
            "ls_single_variant": state.get("ls_single_variant_id", ""),
            "ls_unlimited_variant": state.get("ls_unlimited_variant_id", ""),
            # Version
            "current_version": state.get("version", "1.0.0"),
            "contract_version": parsed.get("build_version", ""),
            # Provenance
            "build_id": state.get("incoming_event", {}).get("data", {}).get("build_id", ""),
            "approved_event_id": state.get("approved_event_id", ""),
            "launch_idempotency_key": ikey,
        }

        try:
            registry.save(record)
        except RegistryError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("REGISTRY_RECORDER | PLT_401 | %s", exc)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_401",
                    "error": f"Registry save failed: {exc}"}

        result = {
            **state,
            "logs": state.get("logs",[]) + [
                f"REGISTRY_RECORDER: ThemeRecord saved wp_post_id={state['wp_post_id']}"
            ],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("REGISTRY_RECORDER | DONE | theme=%s wp_post_id=%s", theme_slug, state["wp_post_id"])
        return result
    return registry_recorder_node

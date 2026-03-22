"""Node: UPDATE_ENTRY — T055"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.update_entry")
NODE_NAME = "UPDATE_ENTRY"
SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

def make_update_entry_node(registry: ProductRegistry):
    def update_entry_node(state: UpdateState) -> dict:
        event = state.get("incoming_event", {})
        data = event.get("data", {})
        theme_slug = data.get("theme_slug", "")
        new_version = data.get("new_version", "")
        ikey = f"update:{theme_slug}:{new_version}"

        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        # schema_version check
        if event.get("schema_version", "1.0") not in SUPPORTED_SCHEMA_VERSIONS:
            return {**state, "idempotency_key": ikey, "theme_slug": theme_slug,
                    "new_version": new_version,
                    "status": PlatformStatus.FAILED, "error_code": "PLT_804",
                    "error": "schema_version غير مدعوم"}

        result = {
            **state,
            "idempotency_key": ikey,
            "theme_slug": theme_slug,
            "new_version": new_version,
            "event_id": event.get("event_id", ""),
            "package_path": data.get("package_path", ""),
            "changelog": data.get("changelog", {}),
            "status": PlatformStatus.RUNNING,
            "error_code": None, "error": None,
            "logs": state.get("logs",[]) + [f"UPDATE_ENTRY: {theme_slug} → v{new_version}"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("UPDATE_ENTRY | DONE | %s → v%s", theme_slug, new_version)
        return result
    return update_entry_node

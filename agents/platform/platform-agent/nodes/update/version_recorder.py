"""Node: VERSION_RECORDER — T062"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry, RegistryError
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.version_recorder")
NODE_NAME = "VERSION_RECORDER"

def make_version_recorder_node(registry: ProductRegistry):
    def version_recorder_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)
        try:
            registry.update_version(
                theme_slug=state["theme_slug"],
                new_version=state["new_version"],
                event_id=state.get("event_id", ""),
                idempotency_key=ikey,
            )
        except RegistryError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_401",
                    "error": f"Version update failed: {exc}"}
        result = {**state, "logs": state.get("logs",[]) + [f"VERSION_RECORDER: v{state['new_version']} saved"]}
        mark_completed(registry.db, ikey, NODE_NAME, result)
        return result
    return version_recorder_node

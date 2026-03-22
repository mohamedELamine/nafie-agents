"""Node: LS_FILE_UPDATER — T059 | السعر لا يُمس (Constitution V)"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from services.ls_client import LemonSqueezyClient, LemonSqueezyError
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.ls_file_updater")
NODE_NAME = "LS_FILE_UPDATER"

def make_ls_file_updater_node(registry: ProductRegistry, ls_client: LemonSqueezyClient):
    def ls_file_updater_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        ls_product_id = state["ls_product_id"]
        package_path = state.get("package_path", "")

        try:
            ls_client.update_product_file(ls_product_id, package_path)
        except LemonSqueezyError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_704",
                    "error": f"LS file update failed: {exc}"}

        result = {**state, "logs": state.get("logs",[]) + [f"LS_FILE_UPDATER: product_id={ls_product_id} file updated"]}
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("LS_FILE_UPDATER | DONE | product_id=%s", ls_product_id)
        return result
    return ls_file_updater_node

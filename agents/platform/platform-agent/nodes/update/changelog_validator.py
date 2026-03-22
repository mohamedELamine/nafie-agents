"""Node: CHANGELOG_VALIDATOR — T056 | Constitution X"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.changelog_validator")
NODE_NAME = "CHANGELOG_VALIDATOR"
VALID_TYPES = {"patch", "minor", "major"}

def make_changelog_validator_node(registry: ProductRegistry):
    def changelog_validator_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        changelog = state.get("changelog", {})
        errors = []
        if not changelog.get("summary_ar", "").strip():
            errors.append("summary_ar فارغ")
        items = changelog.get("items_ar", [])
        if not isinstance(items, list) or len(items) == 0:
            errors.append("items_ar فارغة")
        if changelog.get("type") not in VALID_TYPES:
            errors.append(f"type يجب أن يكون: {VALID_TYPES}")
        if not isinstance(changelog.get("is_security"), bool):
            errors.append("is_security يجب أن يكون bool")

        if errors:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("CHANGELOG_VALIDATOR | PLT_803 | %s", errors)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_803",
                    "error": f"Changelog غير صالح: {errors}"}

        result = {**state, "logs": state.get("logs",[]) + ["CHANGELOG_VALIDATOR: PASS"]}
        mark_completed(registry.db, ikey, NODE_NAME, result)
        return result
    return changelog_validator_node

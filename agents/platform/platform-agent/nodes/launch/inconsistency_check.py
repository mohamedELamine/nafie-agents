"""
Node: INCONSISTENCY_CHECK — T041
يمنع إطلاق أي workflow جديد إن كان هناك INCONSISTENT_STATE غير محلول.

Constitution VIII: INCONSISTENT_STATE يُوقف كل workflow مستقبلي للقالب حتى التدخل البشري.
المرجع: spec.md § ٥ | tasks/phase3_launch_workflow.md § T041
"""
from __future__ import annotations

import logging

from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from services.resend_client import ResendClient
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.inconsistency_check")
NODE_NAME = "INCONSISTENCY_CHECK"


def make_inconsistency_check_node(registry: ProductRegistry, resend: ResendClient):

    def inconsistency_check_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        theme_slug = state["theme_slug"]

        if check_completed(registry.db, ikey, NODE_NAME):
            logger.info("INCONSISTENCY_CHECK | SKIP | key=%s", ikey)
            return state

        mark_started(registry.db, ikey, NODE_NAME)

        if registry.has_unresolved_inconsistency(theme_slug):
            logger.critical(
                "INCONSISTENCY_CHECK | BLOCKED | theme=%s | INCONSISTENT_STATE unresolved",
                theme_slug,
            )
            try:
                resend.send_inconsistency_alert(
                    theme_slug=theme_slug,
                    wp_state={"status": "unknown — check manually"},
                    ls_state={"status": "unknown — check manually"},
                    context={"node": NODE_NAME, "idempotency_key": ikey,
                             "reason": "Launch blocked due to unresolved inconsistency"},
                )
            except Exception as exc:
                logger.error("INCONSISTENCY_CHECK | alert failed | %s", exc)

            result = {
                **state,
                "status": PlatformStatus.INCONSISTENT_EXTERNAL_STATE,
                "error_code": "PLT_303",
                "error": f"القالب '{theme_slug}' لديه INCONSISTENT_STATE غير محلول — توقف الـ workflow",
                "logs": state.get("logs", []) + ["INCONSISTENCY_CHECK: BLOCKED"],
            }
            mark_completed(registry.db, ikey, NODE_NAME, result)
            return result

        result = {
            **state,
            "logs": state.get("logs", []) + ["INCONSISTENCY_CHECK: PASS"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("INCONSISTENCY_CHECK | PASS | theme=%s", theme_slug)
        return result

    return inconsistency_check_node

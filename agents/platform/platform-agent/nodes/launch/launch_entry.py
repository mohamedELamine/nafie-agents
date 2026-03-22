"""
Node: LAUNCH_ENTRY — T040
أول نقطة في Launch Workflow. يتحقق من صحة الحدث ويُنشئ idempotency_key.

المرجع: spec.md § ٦ | tasks/phase3_launch_workflow.md § T040
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from state import LaunchState, PlatformStatus

if TYPE_CHECKING:
    pass

logger = logging.getLogger("platform_agent.nodes.launch.launch_entry")

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
NODE_NAME = "LAUNCH_ENTRY"


def make_launch_entry_node(registry: ProductRegistry):
    """
    Factory — يعيد launch_entry_node مع registry مربوط.
    """

    def launch_entry_node(state: LaunchState) -> dict:
        event = state.get("incoming_event", {})
        data = event.get("data", {})

        theme_slug: str = data.get("theme_slug", "")
        version: str = data.get("version", "")
        schema_version: str = event.get("schema_version", "1.0")

        ikey = f"launch:{theme_slug}:{version}"

        # ── Idempotency: تجاوز إن اكتمل سابقاً ─────────────
        if check_completed(registry.db, ikey, NODE_NAME):
            logger.info("LAUNCH_ENTRY | SKIP | key=%s", ikey)
            return state

        mark_started(registry.db, ikey, NODE_NAME)
        logger.info("LAUNCH_ENTRY | START | theme=%s v=%s", theme_slug, version)

        # ── T040-1: تحقق من schema_version ──────────────────
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            logger.error("LAUNCH_ENTRY | PLT_804 | schema_version=%s", schema_version)
            result = {
                **state,
                "idempotency_key": ikey,
                "theme_slug": theme_slug,
                "version": version,
                "status": PlatformStatus.FAILED,
                "error_code": "PLT_804",
                "error": f"schema_version '{schema_version}' غير مدعوم",
            }
            mark_completed(registry.db, ikey, NODE_NAME, result)
            return result

        # ── T040-2: تحقق من عدم وجود القالب مسبقاً ─────────
        if registry.exists(theme_slug):
            logger.error("LAUNCH_ENTRY | PLT_101 | theme=%s already exists", theme_slug)
            result = {
                **state,
                "idempotency_key": ikey,
                "theme_slug": theme_slug,
                "version": version,
                "status": PlatformStatus.FAILED,
                "error_code": "PLT_101",
                "error": f"القالب '{theme_slug}' مُسجَّل بالفعل في Registry",
            }
            mark_completed(registry.db, ikey, NODE_NAME, result)
            return result

        # ── T040-3: استخرج بيانات الحدث ─────────────────────
        result = {
            **state,
            "idempotency_key": ikey,
            "theme_slug": theme_slug,
            "version": version,
            "approved_event_id": event.get("event_id", ""),
            "theme_contract": data.get("theme_contract", {}),
            "package_path": data.get("package_path", ""),
            "status": PlatformStatus.RUNNING,
            "error_code": None,
            "error": None,
            "revision_count": 0,
            "logs": state.get("logs", []) + [f"LAUNCH_ENTRY: theme={theme_slug} v={version}"],
        }

        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("LAUNCH_ENTRY | DONE | key=%s", ikey)
        return result

    return launch_entry_node

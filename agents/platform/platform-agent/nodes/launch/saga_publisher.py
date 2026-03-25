"""
Node: SAGA_PUBLISHER — T050
ينشر على WordPress ويُفعّل Lemon Squeezy في خطوتين (Saga Pattern).
Compensating actions عند الفشل. لا ضمان ذرية حقيقية.

Saga Failure Matrix:
  WP نجح + LS فشل  → delete WP post     → إن فشل الـ rollback → INCONSISTENT_STATE
  LS نجح + WP فشل  → deactivate LS       → إن فشل الـ rollback → INCONSISTENT_STATE

المرجع: spec.md § ١١ | tasks/phase3 § T050 | constitution.md المبدأ IV
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from services.wp_client import WordPressClient, WordPressError
from services.ls_client import LemonSqueezyClient, LemonSqueezyError
from services.resend_client import ResendClient
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.saga_publisher")
NODE_NAME = "SAGA_PUBLISHER"

def make_saga_publisher_node(
    registry: ProductRegistry,
    wp_client: WordPressClient,
    ls_client: LemonSqueezyClient,
    resend: ResendClient,
):
    def saga_publisher_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        parsed = state.get("parsed", {})
        theme_name_ar = parsed.get("theme_name_ar", state["theme_slug"])
        page_blocks = state.get("page_blocks", "")
        theme_slug = state["theme_slug"]
        ls_product_id = state.get("ls_product_id")

        # ── الخطوة 1: نشر على WordPress ─────────────────────
        wp_post_id = None
        wp_post_url = ""
        try:
            wp_result = wp_client.create_theme_product({
                "title": theme_name_ar,
                "content": page_blocks,
                "status": "publish",
                "slug": theme_slug,
                "meta": {
                    "nafic_theme_slug": theme_slug,
                    "nafic_ls_product_id": ls_product_id,
                },
            })
            wp_post_id = wp_result["id"]
            wp_post_url = wp_result["link"]
            logger.info("SAGA_PUBLISHER | WP published | post_id=%s", wp_post_id)
        except WordPressError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("SAGA_PUBLISHER | PLT_301 | WP failed | %s", exc)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_301",
                    "error": f"WordPress publish failed: {exc}"}

        # ── الخطوة 2: تفعيل Lemon Squeezy ───────────────────
        try:
            ls_client.activate_product(ls_product_id)
            logger.info("SAGA_PUBLISHER | LS activated | product_id=%s", ls_product_id)
        except LemonSqueezyError as exc:
            logger.error("SAGA_PUBLISHER | LS failed → rolling back WP | %s", exc)
            # Compensating: حذف WordPress post
            rollback_ok = wp_client.delete_theme_product(wp_post_id)
            if not rollback_ok:
                # rollback فشل → INCONSISTENT_STATE
                logger.critical("SAGA_PUBLISHER | ROLLBACK FAILED → PLT_303 | theme=%s", theme_slug)
                registry.record_inconsistent_state(
                    theme_slug=theme_slug,
                    wp_state={"wp_post_id": wp_post_id, "status": "published"},
                    ls_state={"ls_product_id": ls_product_id, "status": "draft"},
                    context={"node": NODE_NAME, "idempotency_key": ikey},
                )
                try:
                    resend.send_inconsistency_alert(theme_slug,
                        {"wp_post_id": wp_post_id, "status": "published"},
                        {"ls_product_id": ls_product_id, "status": "draft"})
                except Exception as e:
                    logger.error("saga_publisher | failed to send inconsistency alert theme=%s: %s", theme_slug, e)
                mark_failed(registry.db, ikey, NODE_NAME)
                return {**state,
                        "wp_post_id": wp_post_id,
                        "status": PlatformStatus.INCONSISTENT_EXTERNAL_STATE,
                        "error_code": "PLT_303",
                        "error": "Saga rollback failed — INCONSISTENT_STATE recorded"}
            # rollback نجح → FAILED عادي
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_201",
                    "error": f"LS activation failed (WP rolled back): {exc}"}

        result = {
            **state,
            "wp_post_id": wp_post_id,
            "wp_post_url": wp_post_url,
            "status": PlatformStatus.RUNNING,
            "logs": state.get("logs",[]) + [
                f"SAGA_PUBLISHER: wp_post_id={wp_post_id} ls_product_id={ls_product_id} PUBLISHED"
            ],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("SAGA_PUBLISHER | DONE | wp=%s ls=%s", wp_post_id, ls_product_id)
        return result
    return saga_publisher_node

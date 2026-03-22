"""Node: WP_CONTENT_UPDATER — T058 | wp_post_id من Registry فقط"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from services.wp_client import WordPressClient, WordPressError
from state import UpdateState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.update.wp_content_updater")
NODE_NAME = "WP_CONTENT_UPDATER"

def make_wp_content_updater_node(registry: ProductRegistry, wp_client: WordPressClient):
    def wp_content_updater_node(state: UpdateState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        wp_post_id = state["wp_post_id"]  # من REGISTRY_LOADER — لا من الحدث
        changelog = state.get("changelog", {})
        new_version = state["new_version"]

        changelog_html = (
            f"<h4>ما الجديد في الإصدار {new_version}؟</h4>"
            f"<p>{changelog.get('summary_ar','')}</p>"
            f"<ul>{''.join(f'<li>{i}</li>' for i in changelog.get('items_ar',[]))}</ul>"
        )
        try:
            wp_client.update_theme_product(wp_post_id, {
                "meta": {"nafic_version": new_version, "nafic_changelog": changelog_html},
            })
        except WordPressError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            return {**state, "status": PlatformStatus.FAILED, "error_code": "PLT_703",
                    "error": f"WP update failed: {exc}"}

        result = {**state, "logs": state.get("logs",[]) + [f"WP_CONTENT_UPDATER: post_id={wp_post_id} updated"]}
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("WP_CONTENT_UPDATER | DONE | post_id=%s v%s", wp_post_id, new_version)
        return result
    return wp_content_updater_node

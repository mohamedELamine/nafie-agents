"""
Node: CONTENT_REGISTRY_UPDATE
يُحدّث Content Registry بالجمل الكنونية.
المرجع: spec.md § ١٨
"""
from __future__ import annotations
import logging
from state import ContentState
from models import ContentType

logger = logging.getLogger("content_agent.nodes.registry_updater")


def make_registry_updater_node(registry):
    def registry_updater_node(state: ContentState) -> dict:
        piece   = state.get("content_piece")
        request = state["request"]

        if not piece or not request.theme_slug:
            return {}  # لا شيء للتحديث

        try:
            registry.update_phrases(
                theme_slug   = request.theme_slug,
                content_type = ContentType(request.content_type),
                piece        = piece,
                score        = piece.validation_score,
            )
            logger.info(
                "registry_updater.updated slug=%s score=%.2f",
                request.theme_slug, piece.validation_score,
            )
        except Exception as exc:
            # لا نوقف الـ workflow بسبب فشل غير حرج
            logger.error("registry_updater.failed slug=%s err=%s", request.theme_slug, exc)

        return {}

    return registry_updater_node

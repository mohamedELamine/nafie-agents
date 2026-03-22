"""
Node: PAGE_RENDERER — T048
يحوّل JSON منظم إلى Gutenberg block markup.
ممنوع: LLM-generated markup مباشرة — يجب المرور عبر هذا الـ renderer الثابت.
المرجع: spec.md § ١٥ | tasks/phase3 § T048
"""
from __future__ import annotations
import json
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.page_renderer")
NODE_NAME = "PAGE_RENDERER"

def make_page_renderer_node(registry: ProductRegistry):
    def page_renderer_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        draft = state.get("draft_page_content", {})
        required_sections = draft.get("required_sections", [])

        try:
            blocks = _render_gutenberg(draft)
            _validate_gutenberg_markup(blocks, required_sections)
        except ValueError as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("PAGE_RENDERER | PLT_602 | validation failed | %s", exc)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_602",
                    "error": f"Gutenberg validation فشل: {exc}"}

        result = {
            **state,
            "page_blocks": blocks,
            "logs": state.get("logs",[]) + ["PAGE_RENDERER: Gutenberg markup generated & validated"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("PAGE_RENDERER | DONE | theme=%s", state["theme_slug"])
        return result
    return page_renderer_node


def _render_gutenberg(page_content: dict) -> str:
    """يحوّل page_content JSON إلى Gutenberg block markup HTML."""
    sections = page_content.get("sections", {})
    blocks = []

    # Hero
    hero = sections.get("hero", {})
    if hero:
        screenshot = hero.get("screenshot_url", "")
        img_tag = f'<img src="{screenshot}" alt="{hero.get("headline","")}" />' if screenshot else ""
        blocks.append(
            f'<!-- wp:group {{"className":"nafic-hero"}} -->\n'
            f'<div class="wp-block-group nafic-hero">'
            f'<h1>{hero.get("headline","")}</h1>'
            f'<p>{hero.get("subheadline","")}</p>'
            f'{img_tag}'
            f'<a class="nafic-btn-primary" href="#pricing">{hero.get("cta_text","اشترِ الآن")}</a>'
            f'</div>\n<!-- /wp:group -->'
        )

    # Features
    features = sections.get("features", {})
    if features:
        items_html = "".join(
            f'<div class="nafic-feature"><span>{i.get("icon","")}</span>'
            f'<h3>{i.get("title","")}</h3><p>{i.get("desc","")}</p></div>'
            for i in features.get("items", [])
        )
        blocks.append(
            f'<!-- wp:group {{"className":"nafic-features"}} -->\n'
            f'<div class="wp-block-group nafic-features">'
            f'<h2>{features.get("title","")}</h2>'
            f'<div class="nafic-features-grid">{items_html}</div>'
            f'</div>\n<!-- /wp:group -->'
        )

    # Pricing
    pricing = sections.get("pricing_section", {})
    if pricing:
        plans_html = ""
        for plan in pricing.get("plans", []):
            featured_class = " nafic-plan--featured" if plan.get("featured") else ""
            plans_html += (
                f'<div class="nafic-plan{featured_class}">'
                f'<h3>{plan.get("name","")}</h3>'
                f'<div class="nafic-price">${plan.get("price",0)}</div>'
                f'<p>{plan.get("description","")}</p>'
                f'<a class="nafic-btn-buy" href="#">اشترِ الآن</a>'
                f'</div>'
            )
        blocks.append(
            f'<!-- wp:group {{"className":"nafic-pricing","id":"pricing"}} -->\n'
            f'<div class="wp-block-group nafic-pricing" id="pricing">'
            f'<h2>{pricing.get("title","")}</h2>'
            f'<div class="nafic-plans-grid">{plans_html}</div>'
            f'</div>\n<!-- /wp:group -->'
        )

    # FAQ
    faq = sections.get("faq", {})
    if faq:
        faq_html = "".join(
            f'<details class="nafic-faq-item"><summary>{i.get("q","")}</summary>'
            f'<p>{i.get("a","")}</p></details>'
            for i in faq.get("items", [])
        )
        blocks.append(
            f'<!-- wp:group {{"className":"nafic-faq"}} -->\n'
            f'<div class="wp-block-group nafic-faq">'
            f'<h2>{faq.get("title","")}</h2>{faq_html}'
            f'</div>\n<!-- /wp:group -->'
        )

    return "\n\n".join(blocks)


def _validate_gutenberg_markup(markup: str, required_sections: list) -> None:
    """يتحقق من وجود الأقسام الإلزامية في الـ markup."""
    section_checks = {
        "hero": "nafic-hero",
        "features": "nafic-features",
        "pricing_section": "nafic-pricing",
        "faq": "nafic-faq",
    }
    missing = []
    for section, css_class in section_checks.items():
        if section in required_sections and css_class not in markup:
            missing.append(section)
    if missing:
        raise ValueError(f"أقسام مفقودة في الـ markup: {missing}")

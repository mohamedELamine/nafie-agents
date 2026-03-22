"""
Node: PAGE_WRITER — T047
يولّد JSON منظم لصفحة المنتج بالعربية.
يُنشئ كل الأقسام المطلوبة من required_sections.
المرجع: spec.md § ١٥ | tasks/phase3 § T047
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started, mark_failed
from db.registry import ProductRegistry
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.page_writer")
NODE_NAME = "PAGE_WRITER"

def make_page_writer_node(registry: ProductRegistry):
    def page_writer_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)

        parsed = state.get("parsed", {})
        theme_name_ar = parsed.get("theme_name_ar", state["theme_slug"])
        domain = parsed.get("domain", "general")
        required_sections = parsed.get("required_sections", [])
        assets = state.get("collected_assets", {})
        revision_notes = state.get("revision_notes")

        try:
            page_content = _build_page_json(
                theme_name_ar=theme_name_ar,
                theme_slug=state["theme_slug"],
                domain=domain,
                required_sections=required_sections,
                assets=assets,
                variants=state.get("ls_variants", []),
                revision_notes=revision_notes,
            )
        except Exception as exc:
            mark_failed(registry.db, ikey, NODE_NAME)
            logger.error("PAGE_WRITER | PLT_601 | %s", exc)
            return {**state,
                    "status": PlatformStatus.FAILED,
                    "error_code": "PLT_601",
                    "error": f"فشل توليد محتوى الصفحة: {exc}"}

        result = {
            **state,
            "draft_page_content": page_content,
            "logs": state.get("logs",[]) + [f"PAGE_WRITER: {len(required_sections)} sections generated"],
        }
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("PAGE_WRITER | DONE | theme=%s sections=%s", state["theme_slug"], required_sections)
        return result
    return page_writer_node


def _build_page_json(
    theme_name_ar: str,
    theme_slug: str,
    domain: str,
    required_sections: list,
    assets: dict,
    variants: list,
    revision_notes: str | None,
) -> dict:
    """يبني JSON منظم لمحتوى صفحة المنتج."""
    single_price = 29
    unlimited_price = 79

    sections = {}

    if "hero" in required_sections:
        sections["hero"] = {
            "headline": f"قالب {theme_name_ar} — قالب WordPress عربي احترافي",
            "subheadline": f"قالب متخصص لمجال {domain} باللغة العربية",
            "screenshot_url": assets.get("screenshot", ""),
            "preview_url": assets.get("preview_url", ""),
            "cta_text": "اشترِ الآن",
        }

    if "features" in required_sections:
        sections["features"] = {
            "title": "مميزات القالب",
            "items": [
                {"icon": "⚡", "title": "سرعة فائقة", "desc": "محسّن للأداء والتحميل السريع"},
                {"icon": "📱", "title": "متجاوب بالكامل", "desc": "يعمل على جميع الأجهزة"},
                {"icon": "🇸🇦", "title": "عربي بالكامل", "desc": "RTL أصيل مع خطوط عربية احترافية"},
                {"icon": "🔧", "title": "سهل التخصيص", "desc": "لوحة تحكم بسيطة وقوية"},
            ],
        }

    if "target_audience" in required_sections:
        sections["target_audience"] = {
            "title": "لمن هذا القالب؟",
            "audience": [f"أصحاب متاجر {domain}", "المصممون والمطورون", "الشركات الصغيرة والمتوسطة"],
        }

    if "quality_section" in required_sections:
        sections["quality_section"] = {
            "title": "جودة مضمونة",
            "guarantees": ["كود نظيف ومنظم", "متوافق مع WooCommerce", "دعم فني سنة كاملة"],
        }

    if "pricing_section" in required_sections:
        sections["pricing_section"] = {
            "title": "اختر خطتك",
            "plans": [
                {
                    "name": "ترخيص واحد",
                    "price": single_price,
                    "currency": "USD",
                    "activations": 1,
                    "description": "مثالي لمشروع واحد",
                },
                {
                    "name": "ترخيص غير محدود",
                    "price": unlimited_price,
                    "currency": "USD",
                    "activations": "غير محدود",
                    "description": "للوكالات والمطورين",
                    "featured": True,
                },
            ],
        }

    if "faq" in required_sections:
        sections["faq"] = {
            "title": "الأسئلة الشائعة",
            "items": [
                {"q": "هل القالب يدعم اللغة العربية بالكامل؟", "a": "نعم، مصمم أصلاً للعربية مع دعم كامل لـ RTL."},
                {"q": "ما مدة الدعم الفني؟", "a": "سنة كاملة من تاريخ الشراء."},
                {"q": "هل يشمل التحديثات المستقبلية؟", "a": "نعم، تحديثات مجانية طوال فترة الترخيص."},
            ],
        }

    if "cta" in required_sections:
        sections["cta"] = {
            "title": f"ابدأ مع {theme_name_ar} اليوم",
            "button_text": "اشترِ الآن",
            "demo_text": "شاهد العرض التجريبي",
            "demo_url": assets.get("preview_url", ""),
        }

    if "woocommerce_features" in required_sections:
        sections["woocommerce_features"] = {
            "title": "تكامل WooCommerce الكامل",
            "items": ["صفحات منتج محسّنة", "سلة تسوق عربية", "صفحة دفع مخصصة"],
        }

    if "cod_features" in required_sections:
        sections["cod_features"] = {
            "title": "الدفع عند الاستلام",
            "items": ["دعم كامل للدفع نقداً", "إدارة طلبات COD", "إشعارات WhatsApp"],
        }

    # إضافة ملاحظات المراجعة إن وُجدت
    if revision_notes:
        sections["_revision_notes"] = revision_notes

    return {
        "theme_slug": theme_slug,
        "theme_name_ar": theme_name_ar,
        "sections": sections,
        "required_sections": required_sections,
    }

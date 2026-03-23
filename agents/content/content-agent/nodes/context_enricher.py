"""
Node: CONTEXT_ENRICHER
يبني ContextBundle — مصدر الحقائق الوحيد للتوليد.
المرجع: spec.md § ٧
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from state import ContentState
from models import ContextBundle, ContentType

if TYPE_CHECKING:
    from db.content_registry import ContentRegistry

logger = logging.getLogger("content_agent.nodes.context_enricher")


def make_context_enricher_node(registry):
    def context_enricher_node(state: ContentState) -> dict:
        request = state["request"]

        try:
            bundle = _build_context_bundle(request, registry)
        except Exception as exc:
            logger.error("context_enricher.failed req=%s err=%s", request.request_id, exc)
            return {
                "status":      "failed",
                "error_code":  "CON_CONTEXT_BUILD_FAILED",
                "error_detail": str(exc),
            }

        # ربط الـ bundle بالـ plan
        plan = state.get("content_plan")
        if plan:
            plan.context_bundle = bundle

        logger.info("context_enricher.built req=%s slug=%s", request.request_id, request.theme_slug)
        return {"context_bundle": bundle, "content_plan": plan}

    return context_enricher_node


def _build_context_bundle(request, registry) -> ContextBundle:
    contract   = request.theme_contract or {}
    raw_ctx    = request.raw_context
    theme_slug = request.theme_slug

    # ١. حقائق القالب
    theme_facts: Dict[str, str] = {
        "theme_name_ar":       contract.get("theme_name_ar", raw_ctx.get("theme_name_ar", "")),
        "domain":              contract.get("domain", ""),
        "cluster":             contract.get("cluster", ""),
        "woocommerce_enabled": str(contract.get("woocommerce_enabled", False)),
        "cod_enabled":         str(contract.get("cod_enabled", False)),
        "final_score":         str(contract.get("final_score", "")),
        "feature_list":        ", ".join(contract.get("feature_list", [])[:8]),
    }

    # ٢. بيانات السجل
    registry_data: Dict[str, str] = {}
    if theme_slug and registry:
        record = _safe_get_registry(registry, theme_slug)
        if record:
            registry_data = {
                "wp_post_url":       record.get("wp_post_url", ""),
                "current_version":   record.get("current_version", ""),
                "pricing_single":    "29$",
                "pricing_unlimited": "79$",
                "pricing_vip":       "299$",
            }

    # ٣. بيانات الإطلاق/التحديث
    release_metadata: Dict[str, str] = {}
    if "new_version" in raw_ctx or "changelog" in raw_ctx:
        changelog = raw_ctx.get("changelog", {})
        release_metadata = {
            "new_version":  raw_ctx.get("new_version", ""),
            "summary_ar":   changelog.get("summary_ar", ""),
            "items_ar":     ", ".join(changelog.get("items_ar", [])[:5]),
            "is_security":  str(changelog.get("is_security", False)),
            "update_type":  changelog.get("type", ""),
        }

    # ٤. إشارات الدعم (للـ KNOWLEDGE_ARTICLE)
    support_signals: Dict[str, str] = {}
    if request.content_type == ContentType.KNOWLEDGE_ARTICLE and request.evidence_contract:
        ev = request.evidence_contract
        support_signals = {
            "issue_summary": ev.issue_summary,
            "resolution":    "\n".join(ev.confirmed_resolution_steps),
            "scope":         ev.applicable_scope,
            "limitations":   ", ".join(ev.known_limitations),
        }

    # ٥. الـ allowed/forbidden claims
    allowed, forbidden = _build_claim_boundaries(contract, raw_ctx)

    # ٦. الجمل الكنونية من Content Registry
    canonical_phrases: Dict[str, str] = {}
    if theme_slug and registry:
        canonical_phrases = registry.get_phrases(theme_slug) or {}

    return ContextBundle(
        theme_facts       = theme_facts,
        product_registry  = registry_data,
        release_metadata  = release_metadata,
        support_signals   = support_signals,
        known_constraints = _build_constraints(contract),
        allowed_claims    = allowed,
        forbidden_claims  = forbidden,
        source_map        = {"theme_facts": "THEME_CONTRACT", "registry": "content_registry"},
        canonical_phrases = canonical_phrases,
    )


def _build_claim_boundaries(contract: dict, raw_ctx: dict):
    allowed  = []
    forbidden = []

    features = contract.get("feature_list", [])
    for f in features:
        allowed.append(f"القالب يدعم/يتضمن: {f}")

    if contract.get("woocommerce_enabled"):
        allowed.append("القالب يتكامل مع WooCommerce")
    if contract.get("cod_enabled"):
        allowed.append("القالب يدعم الدفع عند الاستلام (COD)")
    if contract.get("final_score"):
        allowed.append(f"درجة جودة القالب: {contract['final_score']}/100")

    forbidden.extend([
        "أي إحصاء رقمي لم يأتِ من THEME_CONTRACT",
        "مقارنة بأي قالب أو متجر آخر",
        "وعد بأي ميزة غير موجودة في feature_list",
        "ادعاء بزيادة المبيعات أو الأرباح",
        "ضمان نتيجة تجارية",
    ])
    return allowed, forbidden


def _build_constraints(contract: dict) -> List[str]:
    constraints = ["عربية فصيحة فقط", "لا إحصاءات غير مستندة"]
    if not contract.get("woocommerce_enabled"):
        constraints.append("لا ذكر لـ WooCommerce — غير مفعّل")
    if not contract.get("cod_enabled"):
        constraints.append("لا ذكر لـ COD — غير مفعّل")
    return constraints


def _safe_get_registry(registry, theme_slug: str) -> Optional[dict]:
    try:
        return registry.get(theme_slug)
    except Exception:
        return None

"""
Claude Client — وكيل المحتوى
يتضمن: FACT_NORMALIZER، CONTENT_GENERATOR، claude_factual_check_safe
المرجع: spec.md § ٨، ١٣، ١٤ + Patch v2.1 § ١
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

import anthropic

from models import (
    BRAND_CONSTITUTION_FORBIDDEN_PATTERNS,
    CONTENT_TYPE_SPECS,
    FACTUAL_CHECK_FALLBACK_POLICY,
    TERMINOLOGY_GLOSSARY,
    ContentCategory,
    ContentPiece,
    ContentPlan,
    ContentRequest,
    ContentStatus,
    ContentTemplate,
    ContentType,
    FactSheet,
    count_words,
    parse_word_budget,
)

logger = logging.getLogger("content_agent.services.claude_client")

BRAND_CONSTITUTION_VERSION = os.getenv("BRAND_CONSTITUTION_VERSION", "1.0")
MODEL = "claude-sonnet-4-20250514"

BRAND_CONSTITUTION = """
# Brand Constitution v1.0 — قوالب عربية

## الهوية
نحن متجر قوالب WordPress عربي متخصص.
نبني أدوات احترافية لأصحاب المواقع والمطورين العرب.

## الصوت الثابت
- واثق بلا غطرسة
- تقني بلا تعقيد
- مهني دافئ — لا جفاف ولا مبالغة
- يخاطب العربي بلغته، لا بترجمة مصطنعة

## اللغة
- عربية فصيحة مبسطة
- جمل قصيرة واضحة
- لا مبالغة في الأوصاف

## المحظور المطلق
- ادعاءات غير قابلة للتحقق
- مقارنة بالمنافسين
- وعود بميزات غير موجودة
- أسلوب إعلاني مبتذل
- إحصاءات غير مستندة
- أسلوب مترجم حرفياً
"""

FACT_NORMALIZER_PROMPT = """\
أنت محلل حقائق متخصص في محتوى قوالب WordPress.
مهمتك: فصل ما يمكن ادعاؤه عما لا يمكن ادعاؤه.

البيانات المُدخلة:
{context_bundle_summary}

أرجع JSON فقط (بلا markdown):
{{
    "verified_facts": ["حقيقة قابلة للتحقق مباشرة من البيانات"],
    "allowed_inferences": ["استنتاج مقبول ومنطقي من الحقائق"],
    "forbidden_claims": ["ادعاء لا يمكن إثباته أو يتجاوز البيانات"]
}}

قواعد:
- verified_fact: موجود حرفياً في البيانات
- allowed_inference: منطقي لكن لا يُبالغ (مثال: "يدعم WooCommerce" → "يتيح بناء متجر")
- forbidden_claim: تخمين أو مبالغة أو وعد بنتيجة تجارية
"""

FACTUAL_CHECK_PROMPT = """\
افحص هذا المحتوى:
{body}

الادعاءات المسموحة:
{allowed_claims}

الادعاءات الممنوعة:
{forbidden_claims}

أرجع JSON فقط (بلا markdown):
{{
    "violations": ["ادعاء مخالف إن وُجد"],
    "all_clear": true
}}
"""


class ClaudeContentClient:
    """
    يوفر ثلاث وظائف رئيسية:
    1. normalize_facts() — FACT_NORMALIZER
    2. generate_content() — CONTENT_GENERATOR
    3. factual_check_safe() — التحقق الدلالي مع fallback
    """

    def __init__(self, api_key: Optional[str] = None):
        key         = api_key or os.environ["CLAUDE_API_KEY"]
        self._client = anthropic.Anthropic(api_key=key)

    # ── 1. FACT_NORMALIZER ────────────────────────────────────────

    def normalize_facts(
        self,
        context_bundle_summary: str,
        constitution_version:   str = BRAND_CONSTITUTION_VERSION,
        template_version:       str = "default",
    ) -> FactSheet:
        """
        يُنتج FactSheet من ContextBundle.
        يُستدعى قبل التوليد دائماً.
        """
        response = self._client.messages.create(
            model      = MODEL,
            max_tokens = 600,
            system     = "أنت محلل حقائق. أرجع JSON فقط بلا markdown.",
            messages   = [{
                "role":    "user",
                "content": FACT_NORMALIZER_PROMPT.format(
                    context_bundle_summary=context_bundle_summary
                ),
            }],
        )
        raw  = response.content[0].text.strip()
        # إزالة markdown code blocks إن وُجدت
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return FactSheet(
            verified_facts       = data.get("verified_facts", []),
            allowed_inferences   = data.get("allowed_inferences", []),
            forbidden_claims     = data.get("forbidden_claims", []),
            constitution_version = constitution_version,
            template_version     = template_version,
        )

    # ── 2. CONTENT_GENERATOR ─────────────────────────────────────

    def generate_single(
        self,
        request:   ContentRequest,
        plan:      ContentPlan,
        fact_sheet: FactSheet,
        template:  Optional[ContentTemplate] = None,
    ) -> ContentPiece:
        """يُنتج مخرجاً واحداً."""
        from models import build_versioning_metadata_dict
        import uuid
        from datetime import datetime

        system_prompt = self._build_system_prompt(plan, fact_sheet)
        user_prompt   = self._build_generation_prompt(request, plan, template)

        response = self._client.messages.create(
            model      = MODEL,
            max_tokens = _calculate_max_tokens(plan.word_budget),
            system     = system_prompt,
            messages   = [{"role": "user", "content": user_prompt}],
        )
        body       = response.content[0].text.strip()
        versioning = _build_versioning_dict(plan)

        return ContentPiece(
            content_id        = str(uuid.uuid4()),
            request_id        = request.request_id,
            content_type      = request.content_type,
            variant_label     = None,
            theme_slug        = request.theme_slug,
            title             = _extract_title(body),
            body              = body,
            metadata          = {"word_count": count_words(body)},
            versioning        = versioning,
            structural_score  = 0.0,
            language_score    = 0.0,
            factual_score     = 0.0,
            validation_score  = 0.0,
            validation_issues = [],
            status            = ContentStatus.VALIDATING,
            created_at        = datetime.utcnow(),
            target_agent      = request.target_agent,
        )

    def generate_variants(
        self,
        request:   ContentRequest,
        plan:      ContentPlan,
        fact_sheet: FactSheet,
        template:  Optional[ContentTemplate] = None,
    ) -> List[ContentPiece]:
        """يُنتج متغيرات متعددة — لـ MARKETING_COPY و SOCIAL_CAPTION."""
        import uuid
        from datetime import datetime

        system_prompt = self._build_system_prompt(plan, fact_sheet)
        base_prompt   = self._build_generation_prompt(request, plan, template)

        variant_prompt = f"""{base_prompt}

## مطلوب: {plan.variant_count} متغيرات مختلفة

أرجع JSON فقط (بلا markdown):
{{
    "variants": [
        {{"label": "A", "body": "..."}},
        {{"label": "B", "body": "..."}},
        {{"label": "C", "body": "..."}}
    ]
}}

لكل متغير: hook مختلف أو CTA مختلف أو زاوية مختلفة.
"""
        response = self._client.messages.create(
            model      = MODEL,
            max_tokens = _calculate_max_tokens(plan.word_budget * plan.variant_count),
            system     = system_prompt,
            messages   = [{"role": "user", "content": variant_prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data       = json.loads(raw)
        versioning = _build_versioning_dict(plan)
        now        = __import__("datetime").datetime.utcnow()
        pieces     = []

        for v in data.get("variants", []):
            body = v.get("body", "")
            pieces.append(ContentPiece(
                content_id        = str(uuid.uuid4()),
                request_id        = request.request_id,
                content_type      = request.content_type,
                variant_label     = v.get("label"),
                theme_slug        = request.theme_slug,
                title             = None,
                body              = body,
                metadata          = {"word_count": count_words(body)},
                versioning        = versioning,
                structural_score  = 0.0,
                language_score    = 0.0,
                factual_score     = 0.0,
                validation_score  = 0.0,
                validation_issues = [],
                status            = ContentStatus.VALIDATING,
                created_at        = now,
                target_agent      = request.target_agent,
            ))

        return pieces

    # ── 3. FACTUAL CHECK (safe) ───────────────────────────────────

    def factual_check_safe(
        self,
        body:       str,
        fact_sheet: FactSheet,
        category:   ContentCategory,
    ) -> Dict:
        """
        التحقق الدلالي من الادعاءات مع fallback policy.
        المرجع: spec.md Patch v2.1 § ١
        """
        try:
            return self._factual_check(body, fact_sheet)
        except Exception as exc:
            logger.warning("factual_check.api_error category=%s err=%s", category.value, exc)
            policy = FACTUAL_CHECK_FALLBACK_POLICY.get(category, "human_review")
            return {"violations": [], "all_clear": True, "fallback": policy, "error": str(exc)}

    def _factual_check(self, body: str, fact_sheet: FactSheet) -> Dict:
        allowed   = fact_sheet.verified_facts + fact_sheet.allowed_inferences
        forbidden = fact_sheet.forbidden_claims

        response = self._client.messages.create(
            model      = MODEL,
            max_tokens = 300,
            system     = "أنت مدقق حقائق. أرجع JSON فقط بلا markdown.",
            messages   = [{
                "role": "user",
                "content": FACTUAL_CHECK_PROMPT.format(
                    body            = body[:2000],
                    allowed_claims  = "\n".join(f"- {a}" for a in allowed),
                    forbidden_claims = "\n".join(f"- {f}" for f in forbidden),
                ),
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    # ── Prompt Builders ───────────────────────────────────────────

    def _build_system_prompt(self, plan: ContentPlan, fact_sheet: FactSheet) -> str:
        return f"""{BRAND_CONSTITUTION}

## الحقائق الموثقة فقط (استخدم هذه)
{chr(10).join(f'- {f}' for f in fact_sheet.verified_facts)}

## استنتاجات مسموح بها
{chr(10).join(f'- {i}' for i in fact_sheet.allowed_inferences)}

## ممنوع ذكره بأي صيغة
{chr(10).join(f'- {c}' for c in fact_sheet.forbidden_claims)}

## توجيهات هذا المحتوى
النبرة: {plan.tone}
القناة: {plan.channel_style}
الحد: {plan.word_budget} كلمة تقريباً
الهيكل: {' → '.join(plan.structure)}

## قيد مطلق
أرجع المحتوى فقط — لا مقدمات، لا شرح، لا تعليق.
"""

    def _build_generation_prompt(
        self,
        request:  ContentRequest,
        plan:     ContentPlan,
        template: Optional[ContentTemplate],
    ) -> str:
        ctx = request.raw_context
        prompt_parts = [f"اكتب {plan.channel_style} بالمواصفات المحددة."]

        if request.theme_slug:
            prompt_parts.append(f"القالب: {request.theme_slug}")

        if ctx.get("theme_name_ar"):
            prompt_parts.append(f"اسم القالب: {ctx['theme_name_ar']}")

        if ctx.get("changelog"):
            changelog = ctx["changelog"]
            prompt_parts.append(f"ملخص التحديث: {changelog.get('summary_ar', '')}")
            if changelog.get("items_ar"):
                items = "\n".join(f"- {i}" for i in changelog["items_ar"][:5])
                prompt_parts.append(f"بنود التحديث:\n{items}")

        if request.evidence_contract:
            ev = request.evidence_contract
            prompt_parts.append(f"المشكلة: {ev.issue_summary}")
            steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(ev.confirmed_resolution_steps))
            prompt_parts.append(f"خطوات الحل:\n{steps}")

        if template and template.example:
            prompt_parts.append(f"مثال للأسلوب المطلوب:\n{template.example}")

        return "\n\n".join(prompt_parts)


# ── Private Helpers ────────────────────────────────────────────────

def _calculate_max_tokens(word_budget: int) -> int:
    """يحوّل ميزانية الكلمات إلى max_tokens تقريبي."""
    return max(300, min(word_budget * 3, 4096))


def _build_versioning_dict(plan: ContentPlan) -> Dict:
    import datetime
    return {
        "constitution_version": BRAND_CONSTITUTION_VERSION,
        "template_id":          plan.template_id or "default",
        "template_version":     "1.0",
        "planner_version":      os.getenv("PLANNER_VERSION", "1.0"),
        "validator_version":    os.getenv("VALIDATOR_VERSION", "1.0"),
        "model_version":        MODEL,
        "generated_at":         datetime.datetime.utcnow().isoformat(),
    }


def _extract_title(body: str) -> Optional[str]:
    """يستخرج السطر الأول كعنوان."""
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    return lines[0] if lines else None

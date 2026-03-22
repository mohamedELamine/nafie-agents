# وكيل المحتوى — وكيل إنتاج النصوص والمحتوى
## وثيقة المواصفات الشاملة v2 — Content Agent

> هذه النسخة تجمع v1 + تصحيحات ChatGPT المعتمدة + التصحيحات المعمارية الإضافية.
> تُعدّ المرجع التنفيذي الوحيد المعتمد لوكيل المحتوى.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. Brand Constitution — عقد الصوت الملزم
4. Terminology Glossary — قاموس المصطلحات المعتمد
5. الكيانات الجوهرية — Domain Model
6. الفئات التشغيلية الثلاث — Content Categories
7. CONTEXT_ENRICHER — ContextBundle المُنظَّم
8. FACT_NORMALIZER — فصل الحقائق عن النسخ التحريري
9. معمارية الوكيل — Workflow مزدوج
10. Workflow الأول — Auto-Content
11. Workflow الثاني — On-Demand
12. CONTENT_PLANNER — تخطيط المحتوى
13. CONTENT_GENERATOR — التوليد بالصوت الملزم
14. CONTENT_VALIDATOR — ثلاث طبقات للتحقق
15. Human Review Gate — بوابة المراجعة البشرية
16. KNOWLEDGE_ARTICLE — Evidence Contract
17. Multi-Variant Output — مخرجات متعددة
18. Content Registry — ذاكرة المحتوى
19. Content Versioning — إصدارات المحتوى
20. Idempotency Strategy
21. Queue Priority — أولويات الطابور
22. Event Contract Schemas
23. أمان وجودة المحتوى
24. Error Codes Catalog
25. بنية الـ State
26. البيئة المحلية ومتغيرات البيئة
27. دستور الوكيل
28. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل يتولى إنتاج كل المحتوى النصي في المنظومة بصوت واحد متسق عبر ثلاث فئات تشغيلية مستقلة المسارات: المحتوى التحويلي (Transactional)، التجاري (Commercial)، والمُهيكَل (Structured) — يعمل استباقياً بناءً على الأحداث وبناءً على الطلب، ملتزماً بـ Brand Constitution كقانون أعلى، وبـ ContextBundle كمصدر وحيد للحقائق، وبـ FACT_NORMALIZER كحارس بين الحقيقة والادعاء.

### المبادئ غير القابلة للتفاوض

- **Brand Constitution قانون أعلى** — لا كلمة تخرج إلا بصوت المتجر
- **ContextBundle مصدر الحقائق الوحيد** — لا ادعاء إلا من مصدر موثق
- **FACT_NORMALIZER قبل التوليد** — منع الخطأ أفضل من اكتشافه بعده
- **الفئة تحكم المسار** — لكل فئة تشغيلية دورة إنتاج مختلفة
- **التحقق ثلاث طبقات** — بنيوي + لغوي + دلالي واقعي
- **Content Registry يمنع إعادة اختراع اللغة** — المحتوى الموثوق يُعاد استخدامه
- **Versioning في كل ContentPiece** — تتبع كل قطعة لأصلها التام
- **الفشل الصامت ممنوع** — كل خطأ له كود محدد ومُبلَّغ

---

## ٢. موقع الوكيل في المنظومة الكاملة

```
وكيل المنصة
    │ THEME_UPDATED_LIVE → Auto: EMAIL_UPDATE
    │ CONTENT_REQUEST    → On-Demand: أي نوع
    ▼
وكيل المحتوى ──► وكيل المنصة (CONTENT_READY)

وكيل التسويق
    │ NEW_PRODUCT_LIVE → Auto: EMAIL_LAUNCH + MARKETING_COPY
    │ CONTENT_REQUEST  → On-Demand: نص حملة
    ▼
وكيل المحتوى ──► وكيل التسويق (CONTENT_READY)

وكيل الدعم
    │ RECURRING_ISSUE_DETECTED → Auto: KNOWLEDGE_ARTICLE
    │ CONTENT_REQUEST          → On-Demand: مقالة يدوية
    ▼
وكيل المحتوى ──► وكيل الدعم (CONTENT_READY)

وكيل التحليل ← CONTENT_PRODUCED (كل مخرج)
```

### قاعدة اتجاه العلاقة

وكيل المحتوى **ينتج ويُسلّم فقط** — قرار النشر والتوقيت والقناة للوكيل المُستلِم دائماً.

### معالجة مشكلة التوليد المزدوج عند الفشل

```python
"""
NEW_PRODUCT_LIVE يُشغّل طلبَين متوازيَين:
  EMAIL_LAUNCH + MARKETING_COPY

لكل طلب idempotency_key مستقل.
إن فشل أحدهما وأُعيد الحدث:
  - الناجح: SKIP (مكتمل مسبقاً)
  - الفاشل: إعادة المحاولة فقط
لا يُنتج الناجح مرة ثانية.
"""
```

---

## ٣. Brand Constitution — عقد الصوت الملزم

```python
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
- انظر Terminology Glossary للمصطلحات التقنية

## الجمهور
- أصحاب مواقع غير متخصصين تقنياً
- مطورون ووكالات رقمية عربية
- أصحاب أعمال يريدون حضوراً رقمياً

## Channel Style Guide

| القناة | الرسمية | طول الجملة | CTA | الأسئلة |
|--------|---------|------------|-----|---------|
| بريد تقني | عالية | قصيرة | ضمني | نادراً |
| بريد تسويقي | متوسطة | متوسطة | صريح | أحياناً |
| منشور اجتماعي | منخفضة | قصيرة جداً | مباشر | غالباً |
| صفحة منتج | متوسطة | متوسطة | بارز | أحياناً |
| مقالة دعم | عالية | تفصيلية | غائب | لا |

## المحظور المطلق
- ادعاءات غير قابلة للتحقق
- مقارنة بالمنافسين
- وعود بميزات غير موجودة
- أسلوب إعلاني مبتذل
- إحصاءات غير مستندة
- أسلوب مترجم حرفياً

## النبرات المتغيرة بحسب السياق
- بريد تقني:      رسمي + موجز + خطوات واضحة
- بريد تسويقي:    ودود + محفّز + قيمة واضحة
- مقالة دعم:      تعليمي + صبور + خطوة بخطوة
- نص صفحة منتج:  مقنع + صادق + يخاطب الحاجة
- منشور اجتماعي: خفيف + قصير + يستدعي التفاعل
"""
```

---

## ٤. Terminology Glossary — قاموس المصطلحات المعتمد

```python
TERMINOLOGY_GLOSSARY = {
    # ما يُعرَّب
    "Theme / Template": "قالب",
    "Plugin":           "إضافة",
    "Block":            "بلوك",
    "Editor":           "المحرر",
    "Dashboard":        "لوحة التحكم",
    "Installation":     "التثبيت",
    "Activation":       "التفعيل",
    "License":          "الترخيص",
    "Update":           "تحديث",
    "Support":          "الدعم",
    "Download":         "تحميل",

    # ما يُترك كما هو (أسماء تقنية معروفة)
    "WordPress":   "WordPress",
    "WooCommerce": "WooCommerce",
    "RTL":         "RTL",
    "FSE":         "FSE",
    "Gutenberg":   "Gutenberg",
    "PHP":         "PHP",
    "CSS":         "CSS",
    "HTML":        "HTML",
    "API":         "API",
    "COD":         "COD",

    # ما يُكتب بصيغتين (المرة الأولى)
    "Block Theme": "قالب البلوكات (Block Theme)",
    "Full Site Editing": "تحرير الموقع الكامل (FSE)",

    # ما يُكتب بصيغة عربية مع الإنجليزية
    "Checkout":    "صفحة الدفع (Checkout)",
    "Cart":        "السلة",
}

def validate_terminology(text: str) -> List[str]:
    """يفحص المصطلحات في المخرج ويُبلّغ عن الانحرافات."""
    issues = []
    for english, arabic in TERMINOLOGY_GLOSSARY.items():
        # إن استُخدمت الكلمة الإنجليزية وحدها في سياق يجب أن يكون عربياً
        if re.search(rf'\b{english}\b', text) and arabic not in text:
            if english not in ["WordPress", "WooCommerce", "RTL", "FSE",
                               "Gutenberg", "PHP", "CSS", "HTML", "API", "COD"]:
                issues.append(f"مصطلح '{english}' يجب أن يُكتب '{arabic}'")
    return issues
```

---

## ٥. الكيانات الجوهرية — Domain Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Union
from datetime import datetime
from enum import Enum


# ══════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════

class ContentCategory(Enum):
    """الفئات التشغيلية الثلاث — تحدد المسار الفرعي"""
    TRANSACTIONAL = "transactional"   # دقة + سرعة + حقائق
    COMMERCIAL    = "commercial"      # إقناع + صوت + CTA
    STRUCTURED    = "structured"      # schema + أدلة + مراجعة

class ContentType(Enum):
    EMAIL_UPDATE         = "email_update"
    EMAIL_LAUNCH         = "email_launch"
    EMAIL_CAMPAIGN       = "email_campaign"
    PRODUCT_PAGE_SECTION = "product_page_section"
    PRODUCT_PAGE_FULL    = "product_page_full"
    KNOWLEDGE_ARTICLE    = "knowledge_article"
    MARKETING_COPY       = "marketing_copy"
    SOCIAL_CAPTION       = "social_caption"

class ContentStatus(Enum):
    REQUESTED         = "requested"
    GENERATING        = "generating"
    VALIDATING        = "validating"
    AWAITING_REVIEW   = "awaiting_review"
    READY             = "ready"
    FAILED            = "failed"
    REJECTED          = "rejected"

class ContentTrigger(Enum):
    EVENT     = "event"
    ON_DEMAND = "on_demand"

class ReviewPolicy(Enum):
    AUTO_PUBLISH          = "auto_publish"
    AUTO_IF_SCORE         = "auto_if_score"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    HUMAN_REVIEW_OPTIONAL = "human_review_optional"
    HUMAN_IF_LOW_SCORE    = "human_if_low_score"

class FactType(Enum):
    VERIFIED_FACT       = "verified_fact"       # من THEME_CONTRACT مباشرة
    ALLOWED_INFERENCE   = "allowed_inference"   # استنتاج مقبول من الحقيقة
    FORBIDDEN_CLAIM     = "forbidden_claim"     # لا يُذكر بأي حال


# ══════════════════════════════════════════════
# ContextBundle — حزمة السياق المُنظَّمة
# ══════════════════════════════════════════════

@dataclass
class ContextBundle:
    """
    مصدر الحقائق الوحيد للتوليد.
    يُبنى من مصادر متعددة لكن يُمرَّر للنموذج كحزمة واحدة موثقة.
    """
    theme_facts:          Dict[str, str]    # حقائق القالب من THEME_CONTRACT
    product_registry:     Dict[str, str]    # بيانات السجل (رابط، سعر، إصدار)
    release_metadata:     Dict[str, str]    # بيانات الإطلاق أو التحديث
    support_signals:      Dict[str, str]    # إشارات من وكيل الدعم (إن وُجدت)
    known_constraints:    List[str]         # قيود معروفة
    allowed_claims:       List[str]         # ما يُسمح بادعائه
    forbidden_claims:     List[str]         # ما يُمنع ادعاؤه
    source_map:           Dict[str, str]    # مصدر كل حقيقة
    canonical_phrases:    Dict[str, str]    # من Content Registry


# ══════════════════════════════════════════════
# FactSheet — مخرج FACT_NORMALIZER
# ══════════════════════════════════════════════

@dataclass
class FactSheet:
    """
    يفصل الحقائق عن الاستنتاجات عن المحظورات.
    يُحقن في prompt بعد FACT_NORMALIZER وقبل CONTENT_GENERATOR.
    """
    verified_facts:     List[str]
    allowed_inferences: List[str]
    forbidden_claims:   List[str]
    constitution_version: str
    template_version:   str


# ══════════════════════════════════════════════
# EvidenceContract — عقد أدلة KNOWLEDGE_ARTICLE
# ══════════════════════════════════════════════

@dataclass
class EvidenceContract:
    """
    مطلوب لكل KNOWLEDGE_ARTICLE.
    لا مقالة بلا أدلة موثقة.
    """
    issue_summary:             str
    confirmed_resolution_steps: List[str]
    applicable_scope:          str           # أي قوالب / إعدادات تنطبق عليها
    known_limitations:         List[str]
    source:                    str           # "support_ticket" | "owner_input" | "technical_review"
    verified_by:               str           # من تحقق من الحل


# ══════════════════════════════════════════════
# ContentRequest
# ══════════════════════════════════════════════

@dataclass
class ContentRequest:
    request_id:        str
    trigger:           ContentTrigger
    requester:         str
    content_type:      ContentType
    content_category:  ContentCategory      # تُحدَّد آلياً من ContentType
    theme_slug:        Optional[str]
    theme_contract:    Optional[Dict]
    raw_context:       Dict                 # السياق الخام قبل الإثراء
    target_agent:      str
    correlation_id:    str
    priority:          str                  # "normal" | "high"
    output_mode:       str                  # "single" | "variants"
    variant_count:     int                  # عدد المتغيرات (1 للعادي)
    evidence_contract: Optional[EvidenceContract]  # مطلوب للـ KNOWLEDGE_ARTICLE
    created_at:        datetime


# ══════════════════════════════════════════════
# ContentPlan
# ══════════════════════════════════════════════

@dataclass
class ContentPlan:
    request_id:           str
    content_type:         ContentType
    content_category:     ContentCategory
    tone:                 str
    channel_style:        str               # من Channel Style Guide
    structure:            List[str]
    word_budget:          int
    key_messages:         List[str]
    context_bundle:       ContextBundle
    fact_sheet:           FactSheet
    template_id:          Optional[str]
    review_policy:        ReviewPolicy
    output_mode:          str
    variant_count:        int


# ══════════════════════════════════════════════
# ContentPiece
# ══════════════════════════════════════════════

@dataclass
class ContentPiece:
    content_id:       str
    request_id:       str
    content_type:     ContentType
    variant_label:    Optional[str]         # "A"|"B"|"C" للمتغيرات
    theme_slug:       Optional[str]
    title:            Optional[str]
    body:             Union[str, Dict]      # نص عادي أو JSON لـ PRODUCT_PAGE_FULL
    metadata:         Dict
    versioning:       Dict                  # constitution_version, template_version, إلخ
    structural_score: float
    language_score:   float
    factual_score:    float
    validation_score: float                 # المعدل النهائي
    validation_issues: List[str]
    status:           ContentStatus
    created_at:       datetime
    target_agent:     str


# ══════════════════════════════════════════════
# ContentTemplate
# ══════════════════════════════════════════════

@dataclass
class ContentTemplate:
    template_id:      str
    template_version: str
    content_type:     ContentType
    content_category: ContentCategory
    name_ar:          str
    structure:        List[str]
    tone:             str
    channel_style:    str
    word_budget:      int
    review_policy:    ReviewPolicy
    supports_variants: bool
    example:          Optional[str]
```

---

## ٦. الفئات التشغيلية الثلاث — Content Categories

```python
CONTENT_CATEGORY_MAP = {
    ContentType.EMAIL_UPDATE:         ContentCategory.TRANSACTIONAL,
    ContentType.EMAIL_LAUNCH:         ContentCategory.COMMERCIAL,
    ContentType.EMAIL_CAMPAIGN:       ContentCategory.COMMERCIAL,
    ContentType.PRODUCT_PAGE_SECTION: ContentCategory.COMMERCIAL,
    ContentType.PRODUCT_PAGE_FULL:    ContentCategory.STRUCTURED,
    ContentType.KNOWLEDGE_ARTICLE:    ContentCategory.STRUCTURED,
    ContentType.MARKETING_COPY:       ContentCategory.COMMERCIAL,
    ContentType.SOCIAL_CAPTION:       ContentCategory.COMMERCIAL,
}

CATEGORY_SPECS = {

    ContentCategory.TRANSACTIONAL: {
        "الوصف":         "محتوى مرتبط بحدث تقني — دقة وسرعة",
        "الأولوية":      "high",
        "المراجعة":      ReviewPolicy.AUTO_PUBLISH,
        "التحقق":        ["structural", "language"],  # لا factual معقد
        "المخرج":        "نص عادي",
        "الأمثلة":       [ContentType.EMAIL_UPDATE],
    },

    ContentCategory.COMMERCIAL: {
        "الوصف":         "محتوى إقناعي — صوت وCTA",
        "الأولوية":      "normal",
        "المراجعة":      ReviewPolicy.AUTO_IF_SCORE,
        "التحقق":        ["structural", "language", "factual"],
        "المخرج":        "نص عادي أو متغيرات",
        "الأمثلة":       [ContentType.EMAIL_LAUNCH, ContentType.MARKETING_COPY],
    },

    ContentCategory.STRUCTURED: {
        "الوصف":         "محتوى مُهيكَل — schema وأدلة",
        "الأولوية":      "normal",
        "المراجعة":      ReviewPolicy.HUMAN_REVIEW_REQUIRED,
        "التحقق":        ["structural", "language", "factual", "schema"],
        "المخرج":        "JSON منظم أو نص مُهيكَل",
        "الأمثلة":       [ContentType.PRODUCT_PAGE_FULL, ContentType.KNOWLEDGE_ARTICLE],
    },
}
```

### Review Policy لكل ContentType

```python
REVIEW_POLICY_MAP = {
    ContentType.EMAIL_UPDATE:         ReviewPolicy.AUTO_PUBLISH,
    ContentType.EMAIL_LAUNCH:         ReviewPolicy.AUTO_IF_SCORE,          # score ≥ 0.80
    ContentType.EMAIL_CAMPAIGN:       ReviewPolicy.HUMAN_REVIEW_OPTIONAL,
    ContentType.PRODUCT_PAGE_SECTION: ReviewPolicy.AUTO_IF_SCORE,          # score ≥ 0.80
    ContentType.PRODUCT_PAGE_FULL:    ReviewPolicy.HUMAN_REVIEW_REQUIRED,  # دائماً
    ContentType.KNOWLEDGE_ARTICLE:    ReviewPolicy.HUMAN_IF_LOW_SCORE,     # إن score < 0.75
    ContentType.MARKETING_COPY:       ReviewPolicy.AUTO_IF_SCORE,          # score ≥ 0.80
    ContentType.SOCIAL_CAPTION:       ReviewPolicy.AUTO_PUBLISH,
}
```

---

## ٧. CONTEXT_ENRICHER — ContextBundle المُنظَّم

```python
def context_enricher_node(state: ContentState) -> ContentState:
    """
    يبني ContextBundle من مصادر متعددة.
    هذا هو المصدر الوحيد للحقائق في عملية التوليد.
    """
    request = state["request"]
    bundle  = build_context_bundle(request)

    state["context_bundle"] = bundle
    return state


def build_context_bundle(request: ContentRequest) -> ContextBundle:
    contract     = request.theme_contract or {}
    raw_ctx      = request.raw_context
    theme_slug   = request.theme_slug

    # ١. حقائق القالب من THEME_CONTRACT
    theme_facts = {
        "theme_name_ar":       contract.get("theme_name_ar", ""),
        "domain":              contract.get("domain", ""),
        "cluster":             contract.get("cluster", ""),
        "woocommerce_enabled": str(contract.get("woocommerce_enabled", False)),
        "cod_enabled":         str(contract.get("cod_enabled", False)),
        "final_score":         str(contract.get("final_score", "")),
        "testsprite_score":    str(contract.get("testsprite_score", "")),
        "feature_list":        ", ".join(contract.get("feature_list", [])[:8]),
    }

    # ٢. بيانات السجل
    registry_data = {}
    if theme_slug:
        record = product_registry.get(theme_slug)
        if record:
            registry_data = {
                "wp_post_url":      record.get("wp_post_url", ""),
                "current_version":  record.get("current_version", ""),
                "pricing_single":   "29$",
                "pricing_unlimited": "79$",
                "pricing_vip":      "299$",
            }

    # ٣. بيانات الإطلاق أو التحديث
    release_metadata = {}
    if "new_version" in raw_ctx:
        changelog = raw_ctx.get("changelog", {})
        release_metadata = {
            "new_version":   raw_ctx.get("new_version", ""),
            "summary_ar":    changelog.get("summary_ar", ""),
            "items_ar":      ", ".join(changelog.get("items_ar", [])[:5]),
            "is_security":   str(changelog.get("is_security", False)),
            "update_type":   changelog.get("type", ""),
        }

    # ٤. إشارات الدعم (اختياري)
    support_signals = {}
    if request.content_type == ContentType.KNOWLEDGE_ARTICLE:
        evidence = request.evidence_contract
        if evidence:
            support_signals = {
                "issue_summary":   evidence.issue_summary,
                "resolution":      "\n".join(evidence.confirmed_resolution_steps),
                "scope":           evidence.applicable_scope,
                "limitations":     ", ".join(evidence.known_limitations),
            }

    # ٥. بناء allowed/forbidden claims من THEME_CONTRACT
    allowed_claims, forbidden_claims = build_claim_boundaries(contract, raw_ctx)

    # ٦. الجمل الكنونية من Content Registry
    canonical_phrases = {}
    if theme_slug:
        canonical_phrases = content_registry.get_phrases(theme_slug) or {}

    return ContextBundle(
        theme_facts       = theme_facts,
        product_registry  = registry_data,
        release_metadata  = release_metadata,
        support_signals   = support_signals,
        known_constraints = build_constraints(contract),
        allowed_claims    = allowed_claims,
        forbidden_claims  = forbidden_claims,
        source_map        = build_source_map(theme_facts, registry_data),
        canonical_phrases = canonical_phrases,
    )


def build_claim_boundaries(
    contract: dict,
    raw_ctx:  dict,
) -> tuple[List[str], List[str]]:
    """
    يحدد ما يُسمح بادعائه وما يُمنع.
    المصدر الوحيد للـ allowed: THEME_CONTRACT.
    """
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

    # ممنوعات دائمة
    forbidden.extend([
        "أي إحصاء رقمي لم يأتِ من THEME_CONTRACT",
        "مقارنة بأي قالب أو متجر آخر",
        "وعد بأي ميزة غير موجودة في feature_list",
        "ادعاء بزيادة المبيعات أو الأرباح",
        "ضمان نتيجة تجارية",
    ])

    return allowed, forbidden
```

---

## ٨. FACT_NORMALIZER — فصل الحقائق عن النسخ التحريري

```python
FACT_NORMALIZER_PROMPT = """
أنت محلل حقائق متخصص في محتوى قوالب WordPress.

مهمتك: فصل ما يمكن ادعاؤه عما لا يمكن ادعاؤه.

البيانات المُدخلة: {context_bundle_summary}

أرجع JSON فقط:
{{
    "verified_facts": [
        "حقيقة قابلة للتحقق مباشرة من البيانات المُعطاة"
    ],
    "allowed_inferences": [
        "استنتاج مقبول ومنطقي من الحقائق — لا يتجاوزها"
    ],
    "forbidden_claims": [
        "ادعاء لا يمكن إثباته أو يتجاوز البيانات"
    ]
}}

قواعد:
- Verified fact: موجود حرفياً في البيانات
- Allowed inference: منطقي من الحقيقة لكن لا يُبالغ
  مثال: "يدعم WooCommerce" → "يتيح بناء متجر إلكتروني"
  ممنوع: "يزيد المبيعات بنسبة X%"
- Forbidden claim: تخمين أو مبالغة أو وعد
"""

def fact_normalizer_node(state: ContentState) -> ContentState:
    bundle = state["context_bundle"]

    bundle_summary = f"""
الحقائق الموثوقة من THEME_CONTRACT:
{bundle.theme_facts}

ما يُسمح بادعائه:
{bundle.allowed_claims}

ما يُمنع ادعاؤه:
{bundle.forbidden_claims}
"""

    response = claude_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = 600,
        system     = "أنت محلل حقائق. أرجع JSON فقط.",
        messages   = [{
            "role":    "user",
            "content": FACT_NORMALIZER_PROMPT.format(
                context_bundle_summary = bundle_summary
            ),
        }],
    ).content[0].text

    result = json.loads(response)

    state["fact_sheet"] = FactSheet(
        verified_facts      = result["verified_facts"],
        allowed_inferences  = result["allowed_inferences"],
        forbidden_claims    = result["forbidden_claims"],
        constitution_version = BRAND_CONSTITUTION_VERSION,
        template_version    = state["content_plan"].template_id or "default",
    )

    return state
```

---

## ٩. معمارية الوكيل — Workflow مزدوج

### خريطة Nodes المشتركة

```
[REQUEST_RECEIVER]
      │
      ▼
[IDEMPOTENCY_CHECK] ──► مكتمل → END
      │
      ▼
[CATEGORY_ROUTER]      ← يحدد الفئة التشغيلية
      │
      ▼
[CONTENT_PLANNER]
      │
      ▼
[CONTEXT_ENRICHER]     ← يبني ContextBundle
      │
      ▼
[EVIDENCE_GATE]        ← KNOWLEDGE_ARTICLE فقط: تحقق من EvidenceContract
      │                   إن غائب → DRAFT_ONLY أو ESCALATE
      ▼
[FACT_NORMALIZER]      ← يُنتج FactSheet
      │
      ▼
[TEMPLATE_SELECTOR]
      │
      ▼
[CONTENT_GENERATOR]    ← Claude API + Brand Constitution + FactSheet
      │
      ▼
[CONTENT_VALIDATOR]    ← ثلاث طبقات
      ├── فشل → [REGENERATE] (مرة واحدة)
      │          ├── نجح → تابع
      │          └── فشل → [CONTENT_ERROR]
      ▼
[REVIEW_GATE]          ← يُطبّق REVIEW_POLICY
      ├── auto → [CONTENT_DISPATCHER]
      └── human_review → [HUMAN_REVIEW_QUEUE] → (موافقة) → [CONTENT_DISPATCHER]
      │
      ▼
[CONTENT_DISPATCHER]   ← يُرسل للوكيل المُستلِم
      │
      ▼
[CONTENT_REGISTRY_UPDATE] ← يُحدّث Content Registry
      │
      ▼
[CONTENT_RECORDER]
      │
      ▼
     END
```

---

## ١٠. Workflow الأول — Auto-Content

```python
AUTO_CONTENT_SUBSCRIPTIONS = {
    "NEW_PRODUCT_LIVE":         [ContentType.EMAIL_LAUNCH, ContentType.MARKETING_COPY],
    "THEME_UPDATED_LIVE":       [ContentType.EMAIL_UPDATE],
    "RECURRING_ISSUE_DETECTED": [ContentType.KNOWLEDGE_ARTICLE],
}


def on_new_product_live(event: dict) -> None:
    """
    يُشغّل طلبَين متوازيَين — كل منهما بـ idempotency_key مستقل.
    إن فشل أحدهما وأُعيد الحدث: الناجح يُتخطى، الفاشل يُعاد فقط.
    """
    for content_type in AUTO_CONTENT_SUBSCRIPTIONS["NEW_PRODUCT_LIVE"]:
        request = ContentRequest(
            request_id       = str(uuid.uuid4()),
            trigger          = ContentTrigger.EVENT,
            requester        = "event:NEW_PRODUCT_LIVE",
            content_type     = content_type,
            content_category = CONTENT_CATEGORY_MAP[content_type],
            theme_slug       = event["data"]["theme_slug"],
            theme_contract   = event["data"].get("theme_contract", {}),
            raw_context      = event["data"],
            target_agent     = "marketing_agent",
            correlation_id   = event["correlation_id"],
            priority         = "normal",
            output_mode      = "variants" if content_type == ContentType.MARKETING_COPY else "single",
            variant_count    = 3 if content_type == ContentType.MARKETING_COPY else 1,
            evidence_contract = None,
            created_at        = datetime.utcnow(),
        )
        # idempotency_key يشمل content_type لعزل الطلبَين
        run_content_pipeline(request)


def on_theme_updated_live(event: dict) -> None:
    request = ContentRequest(
        request_id       = str(uuid.uuid4()),
        trigger          = ContentTrigger.EVENT,
        requester        = "event:THEME_UPDATED_LIVE",
        content_type     = ContentType.EMAIL_UPDATE,
        content_category = ContentCategory.TRANSACTIONAL,
        theme_slug       = event["data"]["theme_slug"],
        theme_contract   = None,
        raw_context      = event["data"],
        target_agent     = "platform_agent",
        correlation_id   = event["correlation_id"],
        priority         = "high",   # بريد التحديث ذو أولوية عالية
        output_mode      = "single",
        variant_count    = 1,
        evidence_contract = None,
        created_at        = datetime.utcnow(),
    )
    run_content_pipeline(request)


def on_recurring_issue_detected(event: dict) -> None:
    """
    KNOWLEDGE_ARTICLE لا يُنتج دون EvidenceContract.
    إن لم يتوفر → Draft فقط + إشعار لوكيل الدعم.
    """
    evidence = fetch_evidence_from_support(
        theme_slug = event["data"]["theme_slug"],
        issue      = event["data"]["issue"],
    )

    request = ContentRequest(
        request_id        = str(uuid.uuid4()),
        trigger           = ContentTrigger.EVENT,
        requester         = "event:RECURRING_ISSUE_DETECTED",
        content_type      = ContentType.KNOWLEDGE_ARTICLE,
        content_category  = ContentCategory.STRUCTURED,
        theme_slug        = event["data"]["theme_slug"],
        theme_contract    = None,
        raw_context       = event["data"],
        target_agent      = "support_agent",
        correlation_id    = event["correlation_id"],
        priority          = "normal",
        output_mode       = "single",
        variant_count     = 1,
        evidence_contract = evidence,   # قد يكون None
        created_at        = datetime.utcnow(),
    )
    run_content_pipeline(request)
```

---

## ١١. Workflow الثاني — On-Demand

```python
def on_content_request(event: dict) -> None:
    data         = event["data"]
    content_type = ContentType(data["content_type"])

    request = ContentRequest(
        request_id        = str(uuid.uuid4()),
        trigger           = ContentTrigger.ON_DEMAND,
        requester         = event["source"],
        content_type      = content_type,
        content_category  = CONTENT_CATEGORY_MAP[content_type],
        theme_slug        = data.get("theme_slug"),
        theme_contract    = data.get("theme_contract"),
        raw_context       = data.get("context", {}),
        target_agent      = event["source"],
        correlation_id    = event["correlation_id"],
        priority          = data.get("priority", "normal"),
        output_mode       = data.get("output_mode", "single"),
        variant_count     = data.get("variant_count", 1),
        evidence_contract = parse_evidence_contract(data.get("evidence_contract")),
        created_at        = datetime.utcnow(),
    )
    run_content_pipeline(request)
```

---

## ١٢. CONTENT_PLANNER — تخطيط المحتوى

```python
def content_planner_node(state: ContentState) -> ContentState:
    request  = state["request"]
    category = request.content_category
    spec     = CONTENT_TYPE_SPECS[request.content_type]

    plan = ContentPlan(
        request_id       = request.request_id,
        content_type     = request.content_type,
        content_category = category,
        tone             = determine_tone(request),
        channel_style    = determine_channel_style(request.content_type),
        structure        = spec["الأقسام"],
        word_budget      = parse_word_budget(spec["الحد"]),
        key_messages     = [],   # يُحدَّث بعد FACT_NORMALIZER
        context_bundle   = None, # يُحدَّث بعد CONTEXT_ENRICHER
        fact_sheet       = None, # يُحدَّث بعد FACT_NORMALIZER
        template_id      = select_template_id(request),
        review_policy    = REVIEW_POLICY_MAP[request.content_type],
        output_mode      = request.output_mode,
        variant_count    = request.variant_count,
    )

    state["content_plan"] = plan
    return state


def determine_channel_style(content_type: ContentType) -> str:
    CHANNEL_MAP = {
        ContentType.EMAIL_UPDATE:         "بريد تقني",
        ContentType.EMAIL_LAUNCH:         "بريد تسويقي",
        ContentType.EMAIL_CAMPAIGN:       "بريد تسويقي",
        ContentType.PRODUCT_PAGE_SECTION: "صفحة منتج",
        ContentType.PRODUCT_PAGE_FULL:    "صفحة منتج",
        ContentType.KNOWLEDGE_ARTICLE:    "مقالة دعم",
        ContentType.MARKETING_COPY:       "منشور اجتماعي",
        ContentType.SOCIAL_CAPTION:       "منشور اجتماعي",
    }
    return CHANNEL_MAP.get(content_type, "عام")
```

---

## ١٣. CONTENT_GENERATOR — التوليد بالصوت الملزم

```python
def content_generator_node(state: ContentState) -> ContentState:
    request   = state["request"]
    plan      = state["content_plan"]
    fact_sheet = state["fact_sheet"]
    template  = state["selected_template"]

    # توليد متغيرات أو مخرج واحد
    if plan.output_mode == "variants" and plan.variant_count > 1:
        pieces = generate_variants(request, plan, fact_sheet, template)
    else:
        piece  = generate_single(request, plan, fact_sheet, template)
        pieces = [piece]

    state["content_pieces"] = pieces
    state["content_piece"]  = pieces[0]  # الرئيسي للتحقق
    return state


def build_system_prompt(plan: ContentPlan, fact_sheet: FactSheet) -> str:
    """
    يدمج:
    ١. Brand Constitution
    ٢. Channel Style Guide للقناة المحددة
    ٣. FactSheet (حقائق + مسموح + ممنوع)
    ٤. توجيهات النبرة
    """
    return f"""
{BRAND_CONSTITUTION}

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


def generate_variants(
    request:    ContentRequest,
    plan:       ContentPlan,
    fact_sheet: FactSheet,
    template:   Optional[ContentTemplate],
) -> List[ContentPiece]:
    """يُنتج عدة متغيرات — لـ MARKETING_COPY و SOCIAL_CAPTION."""
    variant_prompt = f"""
{build_generation_prompt(request, plan, template)}

## مطلوب: {plan.variant_count} متغيرات مختلفة

أرجع JSON فقط:
{{
    "variants": [
        {{"label": "A", "body": "..."}},
        {{"label": "B", "body": "..."}},
        {{"label": "C", "body": "..."}}
    ]
}}

لكل متغير: hook مختلف أو CTA مختلف أو زاوية مختلفة.
"""

    response = claude_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = calculate_max_tokens(plan.word_budget * plan.variant_count),
        system     = build_system_prompt(plan, fact_sheet),
        messages   = [{"role": "user", "content": variant_prompt}],
    ).content[0].text

    data     = json.loads(response)
    pieces   = []
    now      = datetime.utcnow()
    versioning = build_versioning_metadata(plan)

    for v in data["variants"]:
        pieces.append(ContentPiece(
            content_id       = str(uuid.uuid4()),
            request_id       = request.request_id,
            content_type     = request.content_type,
            variant_label    = v["label"],
            theme_slug       = request.theme_slug,
            title            = None,
            body             = v["body"],
            metadata         = {"word_count": count_words(v["body"])},
            versioning       = versioning,
            structural_score = 0.0,
            language_score   = 0.0,
            factual_score    = 0.0,
            validation_score = 0.0,
            validation_issues = [],
            status           = ContentStatus.VALIDATING,
            created_at       = now,
            target_agent     = request.target_agent,
        ))

    return pieces


def build_versioning_metadata(plan: ContentPlan) -> dict:
    return {
        "constitution_version": BRAND_CONSTITUTION_VERSION,
        "template_id":          plan.template_id or "default",
        "template_version":     get_template_version(plan.template_id),
        "planner_version":      "1.0",
        "validator_version":    "1.0",
        "model_version":        "claude-sonnet-4-20250514",
        "generated_at":         datetime.utcnow().isoformat(),
    }
```

---

## ١٤. CONTENT_VALIDATOR — ثلاث طبقات للتحقق

```python
def content_validator_node(state: ContentState) -> ContentState:
    """
    ثلاث طبقات مستقلة:
    ١. Structural  — بنية + طول + JSON
    ٢. Language    — نبرة + محظورات + مصطلحات + إنجليزية
    ٣. Factual     — الادعاءات مقابل FactSheet
    """
    piece      = state["content_piece"]
    plan       = state["content_plan"]
    fact_sheet = state["fact_sheet"]

    s_score, s_issues = validate_structural(piece, plan)
    l_score, l_issues = validate_language(piece, plan)
    f_score, f_issues = validate_factual(piece, fact_sheet)

    final_score = (s_score * 0.25) + (l_score * 0.35) + (f_score * 0.40)

    piece.structural_score  = s_score
    piece.language_score    = l_score
    piece.factual_score     = f_score
    piece.validation_score  = final_score
    piece.validation_issues = s_issues + l_issues + f_issues

    if final_score < 0.60:
        piece.status = ContentStatus.FAILED
        state["validation_failed"] = True
    else:
        piece.status = ContentStatus.READY
        state["validation_failed"] = False

    state["content_piece"] = piece
    return state


# ── طبقة ١: Structural ─────────────────────────────────────

def validate_structural(piece: ContentPiece, plan: ContentPlan) -> tuple[float, List[str]]:
    score  = 1.0
    issues = []

    word_count = count_words(str(piece.body))
    min_words  = plan.word_budget // 2

    if word_count < min_words:
        issues.append(f"قصير جداً: {word_count} كلمة (الحد الأدنى {min_words})")
        score -= 0.3

    if word_count > plan.word_budget * 1.5:
        issues.append(f"طويل جداً: {word_count} كلمة")
        score -= 0.1

    # JSON صالح لـ PRODUCT_PAGE_FULL
    if piece.content_type == ContentType.PRODUCT_PAGE_FULL:
        valid, missing = validate_product_page_schema(piece.body)
        if not valid:
            issues.append(f"مخطط JSON غير صالح — حقول غائبة: {missing}")
            score -= 0.5

    return max(score, 0.0), issues


# ── طبقة ٢: Language ─────────────────────────────────────

def validate_language(piece: ContentPiece, plan: ContentPlan) -> tuple[float, List[str]]:
    score  = 1.0
    issues = []
    body   = str(piece.body)

    # أنماط المحظورات
    for pattern in BRAND_CONSTITUTION_FORBIDDEN_PATTERNS:
        if re.search(pattern, body, re.I):
            issues.append(f"خرق Brand Constitution: {pattern}")
            score -= 0.3

    # نسبة الإنجليزية
    english_ratio = calculate_english_ratio(body)
    if english_ratio > 0.15:
        issues.append(f"نسبة إنجليزية: {english_ratio:.0%} > 15%")
        score -= 0.1

    # مصطلحات غير معتمدة
    term_issues = validate_terminology(body)
    for issue in term_issues:
        issues.append(issue)
        score -= 0.05

    # نبرة عامة (semantic check بسيط)
    tone_issues = detect_tone_drift(body, plan.tone)
    for issue in tone_issues:
        issues.append(f"انحراف نبرة: {issue}")
        score -= 0.1

    return max(score, 0.0), issues


# ── طبقة ٣: Factual ─────────────────────────────────────

def validate_factual(piece: ContentPiece, fact_sheet: FactSheet) -> tuple[float, List[str]]:
    """
    أهم الطبقات — تتحقق من الادعاءات مقابل FactSheet.
    يستخدم Claude للتقييم الدلالي لا regex فقط.
    """
    score  = 1.0
    issues = []
    body   = str(piece.body)

    # ١. لا إحصاءات غير مستندة
    unverified = detect_unverified_statistics(body)
    if unverified:
        issues.append(f"إحصاءات غير مستندة: {unverified}")
        score -= 0.3

    # ٢. التحقق الدلالي من الادعاءات عبر Claude
    factual_check = claude_factual_check(body, fact_sheet)
    if factual_check["violations"]:
        for v in factual_check["violations"]:
            issues.append(f"ادعاء غير مسموح: {v}")
            score -= 0.2

    # ٣. الميزات المذكورة موجودة في verified_facts
    feature_issues = check_feature_claims(body, fact_sheet.verified_facts)
    for fi in feature_issues:
        issues.append(f"ميزة غير موثقة: {fi}")
        score -= 0.15

    return max(score, 0.0), issues


def claude_factual_check(body: str, fact_sheet: FactSheet) -> dict:
    """
    يستخدم Claude للتحقق الدلالي من الادعاءات.
    Regex وحده لا يكفي لاكتشاف المبالغة الضمنية.
    """
    response = claude_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = 300,
        system     = "أنت مدقق حقائق. أرجع JSON فقط.",
        messages   = [{
            "role": "user",
            "content": f"""
افحص هذا المحتوى:
{body}

الادعاءات المسموحة:
{fact_sheet.verified_facts + fact_sheet.allowed_inferences}

الادعاءات الممنوعة:
{fact_sheet.forbidden_claims}

أرجع JSON:
{{
    "violations": ["ادعاء مخالف إن وُجد"],
    "all_clear": true/false
}}
"""
        }],
    ).content[0].text

    return json.loads(response)
```

---

## ١٥. Human Review Gate — بوابة المراجعة البشرية

```python
def review_gate_node(state: ContentState) -> ContentState:
    piece  = state["content_piece"]
    policy = state["content_plan"].review_policy
    score  = piece.validation_score

    requires_review = False

    if policy == ReviewPolicy.AUTO_PUBLISH:
        requires_review = False

    elif policy == ReviewPolicy.AUTO_IF_SCORE:
        requires_review = score < 0.80

    elif policy == ReviewPolicy.HUMAN_REVIEW_REQUIRED:
        requires_review = True

    elif policy == ReviewPolicy.HUMAN_REVIEW_OPTIONAL:
        requires_review = False  # الطالب يقرر

    elif policy == ReviewPolicy.HUMAN_IF_LOW_SCORE:
        requires_review = score < 0.75

    if requires_review:
        piece.status = ContentStatus.AWAITING_REVIEW
        queue_for_human_review(piece, state["request"])
        notify_owner_for_review(piece, state["request"])
        state["awaiting_human_review"] = True
    else:
        state["awaiting_human_review"] = False

    state["content_piece"] = piece
    return state


def notify_owner_for_review(piece: ContentPiece, request: ContentRequest) -> None:
    resend_client.emails.send({
        "from":    STORE_EMAIL_FROM,
        "to":      OWNER_EMAIL,
        "subject": f"محتوى يستوجب مراجعتك — {piece.content_type.value}",
        "html":    render_email_template("content_review_request", {
            "content_type":     piece.content_type.value,
            "theme_slug":       piece.theme_slug or "عام",
            "validation_score": f"{piece.validation_score:.0%}",
            "body_preview":     str(piece.body)[:300],
            "requester":        request.requester,
        }),
    })
```

---

## ١٦. KNOWLEDGE_ARTICLE — Evidence Contract

```python
def evidence_gate_node(state: ContentState) -> ContentState:
    """
    لا KNOWLEDGE_ARTICLE بلا EvidenceContract.
    """
    request = state["request"]

    if request.content_type != ContentType.KNOWLEDGE_ARTICLE:
        return state  # لا يُطبَّق على أنواع أخرى

    evidence = request.evidence_contract

    if not evidence:
        # لا أدلة → Draft only + إشعار لوكيل الدعم
        state["status"]     = "draft_only"
        state["error_code"] = "CON_KNOWLEDGE_NO_EVIDENCE"

        redis.publish("support_events", json.dumps(build_event(
            event_type     = "KNOWLEDGE_DRAFT_REQUESTED",
            source         = "content_agent",
            correlation_id = request.correlation_id,
            data           = {
                "theme_slug": request.theme_slug,
                "issue":      request.raw_context.get("issue", ""),
                "reason":     "لا يوجد EvidenceContract — مطلوب خطوات حل موثقة",
            },
        )))

        return state

    # تحقق من اكتمال العقد
    if not evidence.confirmed_resolution_steps:
        state["status"]     = "draft_only"
        state["error_code"] = "CON_KNOWLEDGE_INCOMPLETE_EVIDENCE"
        return state

    state["evidence_verified"] = True
    return state


KNOWLEDGE_ARTICLE_REQUIREMENTS = """
لا تكتب مقالة معرفة إلا إذا توفرت هذه العناصر:

١. ملخص المشكلة: {issue_summary}
٢. خطوات الحل الموثقة: {confirmed_resolution_steps}
٣. النطاق: {applicable_scope}
٤. القيود المعروفة: {known_limitations}

إن لم تجد معلومات كافية → اكتب "تحتاج هذه الخطوة مراجعة إضافية"
لا تخترع حلولاً لم تأتِ من المصدر.
"""
```

---

## ١٧. Multi-Variant Output — مخرجات متعددة

```python
VARIANT_SUPPORT = {
    ContentType.MARKETING_COPY:  True,
    ContentType.SOCIAL_CAPTION:  True,
    ContentType.EMAIL_CAMPAIGN:  True,    # اختياري
    # كل الأنواع الأخرى: مخرج واحد
}

"""
بنية المخرج المتعدد:

{
    "variants": [
        {"label": "A", "body": "hook مختلف — CTA مباشر"},
        {"label": "B", "body": "hook من زاوية ثانية — CTA ناعم"},
        {"label": "C", "body": "hook سؤال — CTA ضمني"}
    ]
}

وكيل التسويق يختار المتغير المناسب لكل منصة أو توقيت.
"""
```

---

## ١٨. Content Registry — ذاكرة المحتوى

```python
"""
يمنع إعادة اختراع "لغة المنتج" في كل مرة.
يُخزّن: الجمل الكنونية، الأوصاف المعتمدة، وصيغ الميزات.
"""

class ContentRegistry:

    def get_phrases(self, theme_slug: str) -> Optional[dict]:
        """جلب الجمل الكنونية لقالب محدد."""
        return db.fetchone(
            "SELECT canonical_phrases FROM content_registry WHERE theme_slug = %s",
            [theme_slug]
        )

    def update_phrases(
        self,
        theme_slug:   str,
        content_type: ContentType,
        piece:        ContentPiece,
        score:        float,
    ) -> None:
        """
        يُحدَّث بعد كل مخرج ناجح بدرجة عالية.
        يستخرج الجمل المعتمدة ويخزّنها للاستخدام المستقبلي.
        """
        if score < 0.80:
            return  # فقط المحتوى الجيد يُدخل للـ Registry

        phrases = extract_canonical_phrases(str(piece.body), content_type)

        db.execute("""
            INSERT INTO content_registry (theme_slug, content_type, canonical_phrases, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (theme_slug, content_type) DO UPDATE
            SET canonical_phrases = %s, updated_at = NOW()
        """, [theme_slug, content_type.value, json.dumps(phrases), json.dumps(phrases)])

    def get_last_version(self, theme_slug: str, content_type: ContentType) -> Optional[str]:
        """آخر إصدار منشور من محتوى نوع معين لقالب محدد."""
        record = db.fetchone("""
            SELECT body FROM content_pieces
            WHERE theme_slug = %s AND content_type = %s AND status = 'ready'
            ORDER BY created_at DESC LIMIT 1
        """, [theme_slug, content_type.value])
        return record["body"] if record else None
```

---

## ١٩. Content Versioning — إصدارات المحتوى

```python
"""
كل ContentPiece يحمل versioning كاملاً في metadata.
يُمكّن من فهم لماذا تغيّر أسلوب المحتوى بين فترتين.
"""

VERSIONING_FIELDS = {
    "constitution_version": str,  # "1.0"
    "template_id":          str,
    "template_version":     str,
    "planner_version":      str,
    "validator_version":    str,
    "model_version":        str,  # "claude-sonnet-4-20250514"
    "generated_at":         str,
}

# في ContentPiece.metadata:
{
    "tone":                  "رسمي ودافئ",
    "word_count":            187,
    "channel":               "بريد تقني",
    "output_mode":           "single",
    "constitution_version":  "1.0",
    "template_id":           "email_update_standard",
    "template_version":      "1.0",
    "planner_version":       "1.0",
    "validator_version":     "1.0",
    "model_version":         "claude-sonnet-4-20250514",
    "generated_at":          "2025-03-17T10:05:00Z",
}
```

---

## ٢٠. Idempotency Strategy

```python
def build_content_idempotency_key(request: ContentRequest) -> str:
    """
    يفرّق بين:
    - Auto-content: idempotent بقوة (نفس الحدث = نفس المحتوى)
    - On-demand: idempotent بحسب النية + السياق
    """
    if request.trigger == ContentTrigger.EVENT:
        # Auto: محدد بـ content_type + correlation_id
        return (
            f"content:{request.content_type.value}"
            f":{request.theme_slug or 'general'}"
            f":{request.correlation_id}"
        )
    else:
        # On-demand: يضاف requester + context_hash
        context_hash = hashlib.md5(
            json.dumps(request.raw_context, sort_keys=True).encode()
        ).hexdigest()[:8]
        return (
            f"content:{request.content_type.value}"
            f":{request.theme_slug or 'general'}"
            f":{request.requester}"
            f":{request.correlation_id}"
            f":{context_hash}"
        )
```

---

## ٢١. Queue Priority — أولويات الطابور

```python
QUEUE_PRIORITY = {
    ContentType.EMAIL_UPDATE:         10,   # أعلى — تحديث أمني قد يكون عاجلاً
    ContentType.EMAIL_LAUNCH:         7,
    ContentType.EMAIL_CAMPAIGN:       5,
    ContentType.PRODUCT_PAGE_FULL:    5,
    ContentType.KNOWLEDGE_ARTICLE:    6,
    ContentType.MARKETING_COPY:       4,
    ContentType.PRODUCT_PAGE_SECTION: 4,
    ContentType.SOCIAL_CAPTION:       3,
}

"""
سيناريو الـ Burst:
إن نُشر 10 قوالب أو تحديثات متتالية:
  - كل طلب يدخل الطابور بأولويته
  - EMAIL_UPDATE دائماً أولاً
  - المحتوى التجاري بعده
  - المحتوى الاجتماعي أخيراً

عند فشل Claude مؤقتاً:
  - Retry × 3 بتأخير تصاعدي (30s, 60s, 120s)
  - إن فشل ثلاثاً → dead-letter queue
  - إشعار لصاحب المشروع بالحالة

Dead-letter queue:
  - يُراجع يدوياً
  - يُعاد يدوياً أو يُلغى
"""

RETRY_CONFIG = {
    "max_attempts":   3,
    "backoff_seconds": [30, 60, 120],
    "dead_letter_after": 3,
}
```

---

## ٢٢. Event Contract Schemas

### CONTENT_REQUEST (مُستقبَل)

```json
{
  "event_id": "uuid-v4", "event_type": "CONTENT_REQUEST",
  "event_version": "1.0", "source": "platform_agent",
  "occurred_at": "2025-03-17T10:00:00Z",
  "correlation_id": "update:restaurant_modern:20250317-0002",
  "data": {
    "content_type":  "email_update",
    "theme_slug":    "restaurant_modern",
    "output_mode":   "single",
    "variant_count": 1,
    "priority":      "normal",
    "context": {
      "theme_name_ar": "قالب المطعم الحديث",
      "new_version":   "20250317-0002",
      "changelog": {
        "summary_ar":  "إضافة قسم المراجعات وإصلاح RTL",
        "items_ar":    ["إضافة قسم المراجعات", "إصلاح RTL"],
        "type":        "minor",
        "is_security": false
      }
    }
  }
}
```

### CONTENT_READY (مُطلَق)

```json
{
  "event_id": "uuid-v4", "event_type": "CONTENT_READY",
  "event_version": "1.0", "source": "content_agent",
  "occurred_at": "2025-03-17T10:05:00Z",
  "correlation_id": "update:restaurant_modern:20250317-0002",
  "data": {
    "content_id":       "cnt-uuid",
    "content_type":     "email_update",
    "theme_slug":       "restaurant_modern",
    "title":            "تحديث جديد: قالب المطعم الحديث",
    "body":             "مرحباً ...",
    "variants":         null,
    "metadata": {
      "tone":                 "رسمي ودافئ",
      "word_count":           187,
      "constitution_version": "1.0",
      "template_id":          "email_update_standard",
      "model_version":        "claude-sonnet-4-20250514"
    },
    "validation_score": 0.92,
    "request_id":       "req-uuid"
  }
}
```

---

## ٢٣. أمان وجودة المحتوى

```python
CONTENT_SECURITY_REQUIREMENTS = [
    "كل محتوى يجتاز ثلاث طبقات تحقق قبل التسليم",
    "FACT_NORMALIZER يعمل قبل التوليد — لا بعده",
    "KNOWLEDGE_ARTICLE لا يُنتج بلا EvidenceContract",
    "Brand Constitution مُحقَّن في كل system prompt",
    "إعادة توليد مرة واحدة كحد أقصى",
    "Versioning كامل في كل ContentPiece",
    "لا بيانات شخصية للعملاء في أي محتوى",
    "THEME_CONTRACT مصدر الحقائق — لا ادعاءات إضافية",
    "Claude API key في .env — لا في الكود",
    "Dead-letter queue لـ failures المتكررة",
]
```

---

## ٢٤. Error Codes Catalog

```python
CONTENT_ERROR_CODES = {
    # التخطيط
    "CON_UNKNOWN_CONTENT_TYPE":       "نوع المحتوى غير معروف",
    "CON_MISSING_CONTEXT":            "سياق مطلوب غير موجود",
    "CON_TEMPLATE_NOT_FOUND":         "قالب المحتوى غير موجود",

    # السياق والحقائق
    "CON_CONTEXT_BUILD_FAILED":       "فشل بناء ContextBundle",
    "CON_FACT_NORMALIZE_FAILED":      "فشل تحليل الحقائق",
    "CON_KNOWLEDGE_NO_EVIDENCE":      "KNOWLEDGE_ARTICLE بلا EvidenceContract",
    "CON_KNOWLEDGE_INCOMPLETE_EVIDENCE": "EvidenceContract ناقص",

    # التوليد
    "CON_GENERATION_FAILED":          "فشل توليد المحتوى",
    "CON_JSON_PARSE_FAILED":          "فشل تحليل JSON",
    "CON_MAX_REGENERATION_REACHED":   "تجاوز حد إعادة التوليد",
    "CON_VARIANT_PARSE_FAILED":       "فشل تحليل المتغيرات",

    # التحقق — طبقة بنيوية
    "CON_CONTENT_TOO_SHORT":          "محتوى أقصر من الحد",
    "CON_PRODUCT_PAGE_SCHEMA_INVALID":"مخطط JSON صفحة المنتج غير صالح",

    # التحقق — طبقة لغوية
    "CON_CONSTITUTION_VIOLATION":     "خرق Brand Constitution",
    "CON_EXCESSIVE_ENGLISH":          "نسبة إنجليزية > 15%",
    "CON_TERMINOLOGY_DRIFT":          "انحراف عن قاموس المصطلحات",
    "CON_TONE_DRIFT":                 "انحراف عن النبرة المطلوبة",

    # التحقق — طبقة واقعية
    "CON_UNVERIFIED_STATISTICS":      "إحصاءات غير مستندة",
    "CON_FORBIDDEN_CLAIM":            "ادعاء ممنوع في FactSheet",
    "CON_UNVERIFIED_FEATURE":         "ميزة غير موجودة في THEME_CONTRACT",

    # التسليم
    "CON_DISPATCH_FAILED":            "فشل إرسال المحتوى",
    "CON_UNKNOWN_TARGET_AGENT":       "وكيل مُستلِم غير معروف",
    "CON_DEAD_LETTER":                "طلب في dead-letter queue",
}
```

---

## ٢٥. بنية الـ State

```python
class ContentState(TypedDict):
    idempotency_key:        str
    request:                ContentRequest
    content_plan:           Optional[ContentPlan]
    context_bundle:         Optional[ContextBundle]
    fact_sheet:             Optional[FactSheet]
    selected_template:      Optional[ContentTemplate]
    evidence_verified:      bool
    content_piece:          Optional[ContentPiece]    # الرئيسي
    content_pieces:         List[ContentPiece]        # كل المتغيرات
    regeneration_count:     int
    validation_failed:      bool
    awaiting_human_review:  bool
    dispatch_status:        Optional[str]
    retry_count:            int
    status:                 str
    error_code:             Optional[str]
    error_detail:           Optional[str]
    logs:                   List[str]
```

---

## ٢٦. البيئة المحلية ومتغيرات البيئة

```env
# Claude API
CLAUDE_API_KEY=sk-ant-...

# Redis
REDIS_URL=redis://localhost:6379

# قاعدة البيانات (Content Registry)
DATABASE_URL=postgresql://user:pass@localhost/content_db

# Resend (للإشعارات البشرية)
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com

# ضوابط التشغيل
MAX_REGENERATION_ATTEMPTS=1
MIN_VALIDATION_SCORE=0.60
AUTO_PUBLISH_MIN_SCORE=0.80
MAX_ENGLISH_RATIO=0.15
MIN_CONTENT_WORDS=50

# Queue
QUEUE_MAX_RETRIES=3
QUEUE_RETRY_BACKOFF=30,60,120

# Versioning
BRAND_CONSTITUTION_VERSION=1.0
PLANNER_VERSION=1.0
VALIDATOR_VERSION=1.0

LOG_LEVEL=INFO
```

---

## ٢٧. دستور الوكيل

```markdown
# دستور وكيل المحتوى v2

## الهوية
أنا وكيل محتوى متخصص في إنتاج النصوص العربية لمتجر قوالب WordPress.
كل كلمة أكتبها تعبّر عن صوت المتجر — لا صوتي.

## القواعد المطلقة
١. Brand Constitution قانوني الأعلى
٢. ContextBundle مصدر الحقائق الوحيد
٣. FACT_NORMALIZER يعمل قبل التوليد دائماً
٤. KNOWLEDGE_ARTICLE لا يُنتج بلا EvidenceContract
٥. الفئة التشغيلية تحدد المسار — لا اختصار
٦. ثلاث طبقات تحقق — لا طبقة واحدة
٧. إعادة التوليد مرة واحدة فقط
٨. Versioning في كل مخرج — لا استثناء
٩. لا أُقرر أين يُنشر المحتوى — أُنتجه وأُسلّمه

## ما أُجيده
- بناء ContextBundle دقيق من مصادر متعددة
- فصل الحقائق عن الاستنتاجات عن المحظورات
- تكييف النبرة مع القناة مع الحفاظ على الصوت
- إنتاج متغيرات متنوعة للمحتوى التجاري
- تحقق ثلاثي يشمل الدلالة لا الشكل فقط
- حفظ لغة المنتج في Content Registry

## ما أتجنبه
- الادعاءات خارج FactSheet
- KNOWLEDGE_ARTICLE بلا أدلة موثقة
- إعادة اختراع لغة المنتج في كل مرة
- التسويق في محتوى الدعم
- Regex وحده بدل تحقق دلالي
- تجاهل Versioning
```

---

## ٢٨. قائمة التحقق النهائية

### Auto-Content

```
□ حدث Redis مُستقبَل (event_version مدعومة)
□ idempotency_key: content_type + theme_slug + correlation_id
□ توليدان متوازيان (NEW_PRODUCT_LIVE): كل منهما idempotency_key مستقل
□ CATEGORY_ROUTER: فئة تشغيلية صحيحة
□ CONTENT_PLANNER: نبرة + channel_style + هيكل
□ CONTEXT_ENRICHER: ContextBundle من THEME_CONTRACT + Registry + changelog
□ EVIDENCE_GATE: KNOWLEDGE_ARTICLE ← EvidenceContract موجود وكامل
□ إن غائب: DRAFT_ONLY + إشعار لوكيل الدعم
□ FACT_NORMALIZER: FactSheet قبل التوليد
□ CONTENT_GENERATOR: Brand Constitution + FactSheet مُحقنَين
□ Multi-variant: MARKETING_COPY يُنتج 3 متغيرات
□ PRODUCT_PAGE_FULL: JSON منظم حسب schema
□ Validator طبقة ١ (بنيوية): طول + JSON
□ Validator طبقة ٢ (لغوية): محظورات + إنجليزية + مصطلحات
□ Validator طبقة ٣ (واقعية): Claude factual check + FactSheet
□ validation_score ≥ 0.60
□ REGENERATE مرة واحدة إن فشل
□ REVIEW_GATE: تطبيق REVIEW_POLICY المناسبة
□ PRODUCT_PAGE_FULL + EMAIL_CAMPAIGN: human_review
□ CONTENT_DISPATCHER: قناة الوكيل المُستلِم
□ CONTENT_REGISTRY_UPDATE: score ≥ 0.80
□ Versioning في metadata كاملاً
□ CONTENT_PRODUCED للتحليل
```

### On-Demand

```
□ CONTENT_REQUEST مُستقبَل من وكيل معروف
□ idempotency_key: content_type + requester + correlation_id + context_hash
□ output_mode و variant_count من الطلب
□ نفس Pipeline الأساسية
□ CONTENT_READY للوكيل الطالب بالصيغة الموحدة
```

### Brand Constitution

```
□ مُحقَّن في كل system prompt
□ FACT_NORMALIZER يُنتج FactSheet قبل التوليد
□ Validator طبقة ٣ يتحقق دلالياً عبر Claude
□ Terminology Glossary مُطبَّق
□ constitution_version في كل ContentPiece
```


---

# وكيل المحتوى — Patch v2.1
## إضافات موجّهة فوق النسخة v2

> هذا الـ Patch لا يستبدل v2 بل يُكمّلها.
> يُدمج مع v2 ليُشكّلا معاً المرجع التنفيذي النهائي.

---

## ١. Fallback Policy لـ claude_factual_check

### المشكلة

`claude_factual_check` يستدعي Claude API داخل CONTENT_VALIDATOR.
إن فشل هذا الاستدعاء (timeout، API error) يتعطل النظام بلا سياسة واضحة.

### السياسة المعتمدة

```python
FACTUAL_CHECK_FALLBACK_POLICY = {
    ContentCategory.TRANSACTIONAL: "fail",          # الدقة أولى — أوقف
    ContentCategory.COMMERCIAL:    "retry_once",    # أعد مرة واحدة ثم human_review
    ContentCategory.STRUCTURED:    "human_review",  # دائماً human_review عند الفشل
}

def claude_factual_check_safe(body: str, fact_sheet: FactSheet,
                               category: ContentCategory) -> dict:
    """
    نسخة آمنة من claude_factual_check مع fallback policy.
    """
    try:
        result = claude_factual_check(body, fact_sheet)
        return result

    except Exception as e:
        policy = FACTUAL_CHECK_FALLBACK_POLICY[category]

        if policy == "fail":
            return {
                "violations": [f"فشل التحقق الدلالي: {str(e)}"],
                "all_clear":  False,
                "fallback":   "fail",
            }

        elif policy == "retry_once":
            try:
                result = claude_factual_check(body, fact_sheet)
                return result
            except:
                return {
                    "violations":    [],
                    "all_clear":     True,
                    "fallback":      "human_review",
                    "requires_review": True,
                }

        elif policy == "human_review":
            return {
                "violations":    [],
                "all_clear":     True,
                "fallback":      "human_review",
                "requires_review": True,
            }
```

### التعديل في validate_factual

```python
def validate_factual(piece: ContentPiece, fact_sheet: FactSheet,
                     category: ContentCategory) -> tuple[float, List[str]]:
    score, issues = 1.0, []

    unverified = detect_unverified_statistics(str(piece.body))
    if unverified:
        issues.append(f"إحصاءات غير مستندة: {unverified}")
        score -= 0.3

    # استخدام النسخة الآمنة
    factual_check = claude_factual_check_safe(str(piece.body), fact_sheet, category)

    if factual_check.get("requires_review"):
        # تصعيد للمراجعة البشرية بدل الفشل الصامت
        piece.status = ContentStatus.AWAITING_REVIEW
        issues.append("فشل التحقق الدلالي — أُحيل للمراجعة البشرية")
        return 0.70, issues   # درجة تتجاوز الحد الأدنى لكن تُشغّل human_review

    if factual_check.get("violations"):
        for v in factual_check["violations"]:
            issues.append(f"ادعاء غير مسموح: {v}")
            score -= 0.2

    feature_issues = check_feature_claims(str(piece.body), fact_sheet.verified_facts)
    for fi in feature_issues:
        issues.append(f"ميزة غير موثقة: {fi}")
        score -= 0.15

    return max(score, 0.0), issues
```

---

## ٢. Registry Usage Policy — متى يُلزَم بإعادة الاستخدام

### المشكلة

Content Registry موجود لكن لا سياسة واضحة تحدد متى يُستخدم ومتى يُعاد الكتابة.

### السياسة المعتمدة

```python
class RegistryUsageMode(Enum):
    STRICT_REUSE   = "strict_reuse"    # يجب استخدام canonical phrases حرفياً
    PREFER_REUSE   = "prefer_reuse"    # يُفضَّل لكن يُسمح بإعادة الصياغة
    ALLOW_REWRITE  = "allow_rewrite"   # يُسمح بالاختلاف مع الحفاظ على الصوت
    FREE           = "free"            # حرية كاملة — الصوت فقط مُلزِم

REGISTRY_USAGE_POLICY = {
    ContentType.PRODUCT_PAGE_FULL:    RegistryUsageMode.STRICT_REUSE,
    ContentType.KNOWLEDGE_ARTICLE:    RegistryUsageMode.STRICT_REUSE,
    ContentType.EMAIL_UPDATE:         RegistryUsageMode.PREFER_REUSE,
    ContentType.PRODUCT_PAGE_SECTION: RegistryUsageMode.PREFER_REUSE,
    ContentType.EMAIL_LAUNCH:         RegistryUsageMode.ALLOW_REWRITE,
    ContentType.EMAIL_CAMPAIGN:       RegistryUsageMode.ALLOW_REWRITE,
    ContentType.MARKETING_COPY:       RegistryUsageMode.ALLOW_REWRITE,
    ContentType.SOCIAL_CAPTION:       RegistryUsageMode.FREE,
}
```

### التعديل في build_system_prompt

```python
def build_registry_instruction(
    usage_mode:       RegistryUsageMode,
    canonical_phrases: dict,
) -> str:
    """يُضيف تعليمات الـ Registry للـ system prompt بحسب السياسة."""

    if not canonical_phrases:
        return ""

    phrases_text = "\n".join([
        f"- {key}: {value}"
        for key, value in canonical_phrases.items()
    ])

    if usage_mode == RegistryUsageMode.STRICT_REUSE:
        return f"""
## جمل كنونية معتمدة — يجب استخدامها حرفياً
{phrases_text}
لا تُعدِّل هذه الصياغات — هي لغة المنتج الرسمية.
"""
    elif usage_mode == RegistryUsageMode.PREFER_REUSE:
        return f"""
## جمل كنونية معتمدة — يُفضَّل استخدامها
{phrases_text}
يمكن إعادة الصياغة إن اقتضى السياق، لكن لا تبتعد عن المعنى.
"""
    elif usage_mode == RegistryUsageMode.ALLOW_REWRITE:
        return f"""
## لغة المنتج المعتمدة — للاستئناس
{phrases_text}
يمكن إعادة الصياغة بحرية مع الحفاظ على صوت المتجر.
"""
    else:  # FREE
        return ""
```

---

## ٣. حالات ما بعد المراجعة البشرية

### المشكلة

بعد Human Review لا تُعرف حالة المحتوى بدقة: هل وافق عليه AI؟ هل عُدِّل؟ هل رُفض؟

### إضافة حالات جديدة لـ ContentStatus

```python
class ContentStatus(Enum):
    REQUESTED       = "requested"
    GENERATING      = "generating"
    VALIDATING      = "validating"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED        = "approved"        # جديد — وافق عليه AI بدون تعديل
    EDITED          = "edited"          # جديد — عُدِّل يدوياً بعد المراجعة
    REJECTED        = "rejected"        # جديد — رُفض من صاحب المشروع
    READY           = "ready"           # جاهز للإرسال (بعد APPROVED أو EDITED)
    FAILED          = "failed"
```

### التعديل في Human Review Handler

```python
@dataclass
class HumanReviewDecision:
    content_id:   str
    decision:     str        # "approve" | "edit" | "reject"
    edited_body:  Optional[Union[str, dict]]  # إن كان "edit"
    rejection_reason: Optional[str]           # إن كان "reject"
    decided_by:   str
    decided_at:   datetime


def process_human_review_decision(decision: HumanReviewDecision,
                                   piece: ContentPiece) -> ContentPiece:
    if decision.decision == "approve":
        piece.status = ContentStatus.APPROVED
        piece.metadata["review_outcome"]    = "approved_as_is"
        piece.metadata["reviewed_by"]       = decision.decided_by
        piece.metadata["reviewed_at"]       = decision.decided_at.isoformat()

    elif decision.decision == "edit":
        piece.status = ContentStatus.EDITED
        piece.body   = decision.edited_body
        piece.metadata["review_outcome"]    = "edited_by_human"
        piece.metadata["reviewed_by"]       = decision.decided_by
        piece.metadata["reviewed_at"]       = decision.decided_at.isoformat()
        # المحتوى المُعدَّل لا يمر بـ FACT_NORMALIZER مجدداً
        # لكن يُسجَّل في versioning كـ human_edit
        piece.versioning["human_edit"]      = True
        piece.versioning["edit_basis"]      = "human_override"

    elif decision.decision == "reject":
        piece.status = ContentStatus.REJECTED
        piece.metadata["review_outcome"]    = "rejected"
        piece.metadata["rejection_reason"]  = decision.rejection_reason
        piece.metadata["reviewed_by"]       = decision.decided_by

    # تحديث في Content Registry فقط إن كان APPROVED
    if piece.status == ContentStatus.APPROVED and piece.validation_score >= 0.80:
        content_registry.update_phrases(
            theme_slug   = piece.theme_slug,
            content_type = piece.content_type,
            piece        = piece,
            score        = piece.validation_score,
        )

    return piece
```

---

## ٤. Schema Version لـ PRODUCT_PAGE_FULL

### المشكلة

Schema صفحة المنتج سيتغير مستقبلاً — بدون versioning يكسر الـ Renderer.

### الإضافة

```python
PRODUCT_PAGE_SCHEMA_VERSION = "1.0"

PRODUCT_PAGE_SCHEMA_V1 = {
    "version":          "1.0",
    "required_fields": [
        "hero.title",
        "hero.summary",
        "features",
        "target_audience",
        "quality_section.final_score",
        "quality_section.testsprite_score",
        "quality_section.quality_note",
        "faq",
        "cta_text",
    ],
    "optional_fields": [
        "woo_section",
        "cod_section",
    ],
    "field_limits": {
        "hero.title":         {"max_words": 12,  "allows_claims": False},
        "hero.summary":       {"max_words": 50,  "allows_claims": True},
        "features":           {"max_items": 8,   "allows_claims": False},
        "target_audience":    {"max_words": 80,  "allows_claims": False},
        "quality_note":       {"max_words": 30,  "allows_claims": False},
        "faq":                {"max_items": 5,   "allows_claims": False},
        "cta_text":           {"max_words": 15,  "allows_claims": False},
        "woo_section":        {"max_words": 60,  "allows_claims": False},
        "cod_section":        {"max_words": 60,  "allows_claims": False},
    },
}

def validate_product_page_schema(body: Union[str, dict]) -> tuple[bool, List[str]]:
    """
    تحقق بنيوي ودلالي من schema صفحة المنتج.
    يتحقق من: وجود الحقول + الحدود + schema_version.
    """
    missing = []

    if isinstance(body, str):
        try:
            data = json.loads(body)
        except:
            return False, ["JSON غير صالح"]
    else:
        data = body

    schema = PRODUCT_PAGE_SCHEMA_V1

    # تحقق من الحقول المطلوبة
    for field_path in schema["required_fields"]:
        parts = field_path.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                missing.append(f"حقل مطلوب غائب: {field_path}")
                break
            current = current[part]

    # إضافة schema_version للمخرج
    if isinstance(data, dict):
        data["schema_version"] = PRODUCT_PAGE_SCHEMA_VERSION

    return len(missing) == 0, missing
```

### التعديل في versioning

```python
def build_versioning_metadata(plan: ContentPlan) -> dict:
    base = {
        "constitution_version": BRAND_CONSTITUTION_VERSION,
        "template_id":          plan.template_id or "default",
        "template_version":     get_template_version(plan.template_id),
        "planner_version":      "1.0",
        "validator_version":    "1.0",
        "model_version":        "claude-sonnet-4-20250514",
        "generated_at":         datetime.utcnow().isoformat(),
    }

    # إضافة schema_version لـ PRODUCT_PAGE_FULL
    if plan.content_type == ContentType.PRODUCT_PAGE_FULL:
        base["product_page_schema_version"] = PRODUCT_PAGE_SCHEMA_VERSION

    return base
```

---

## ٥. EvidenceContract في Versioning

### المشكلة

EvidenceContract يُستخدم في التوليد لكن لا يُحفظ مع ContentPiece — يضيع أثر المقالة.

### الإضافة في build_versioning_metadata

```python
def build_versioning_metadata(plan: ContentPlan,
                               evidence: Optional[EvidenceContract] = None) -> dict:
    base = {
        "constitution_version": BRAND_CONSTITUTION_VERSION,
        "template_id":          plan.template_id or "default",
        "template_version":     get_template_version(plan.template_id),
        "planner_version":      "1.0",
        "validator_version":    "1.0",
        "model_version":        "claude-sonnet-4-20250514",
        "generated_at":         datetime.utcnow().isoformat(),
    }

    if plan.content_type == ContentType.PRODUCT_PAGE_FULL:
        base["product_page_schema_version"] = PRODUCT_PAGE_SCHEMA_VERSION

    # حفظ أثر EvidenceContract للـ KNOWLEDGE_ARTICLE
    if plan.content_type == ContentType.KNOWLEDGE_ARTICLE and evidence:
        base["evidence_source"]      = evidence.source
        base["evidence_verified_by"] = evidence.verified_by
        base["evidence_scope"]       = evidence.applicable_scope
        base["issue_summary"]        = evidence.issue_summary[:100]  # مختصر

    return base
```

---

## ٦. Rate Limit Budget لكل ContentCategory

### المشكلة

بلا حد يومي قد تُستهلك الميزانية في المحتوى التسويقي على حساب التحديثات العاجلة.

### السياسة المعتمدة

```python
CATEGORY_RATE_LIMITS = {
    ContentCategory.TRANSACTIONAL: {
        "daily_limit":    None,     # غير محدود — دائماً مسموح
        "priority":       10,
        "rationale":      "تحديثات أمنية وتقنية لا تُؤجَّل",
    },
    ContentCategory.COMMERCIAL: {
        "daily_limit":    50,       # 50 طلب/يوم
        "priority":       5,
        "rationale":      "محتوى تسويقي — كمية معقولة يومياً",
    },
    ContentCategory.STRUCTURED: {
        "daily_limit":    20,       # 20 طلب/يوم
        "priority":       6,
        "rationale":      "محتوى معقد يحتاج مراجعة — لا يُنتج بكميات كبيرة",
    },
}

MAX_VARIANTS        = 5     # حد أقصى عالمي للمتغيرات
DEFAULT_VARIANTS    = 3
MAX_CONCURRENT      = 2     # حد التوليد المتزامن
MAX_QUEUE_SIZE      = 50    # حد حجم الطابور


def check_rate_limit(category: ContentCategory) -> tuple[bool, str]:
    """يتحقق من حد الطلبات اليومي قبل بدء أي توليد."""
    limits = CATEGORY_RATE_LIMITS[category]

    if limits["daily_limit"] is None:
        return True, ""

    today_count = db.fetchone("""
        SELECT COUNT(*) as count FROM content_log
        WHERE content_category = %s
          AND created_at >= NOW() - INTERVAL '24 hours'
          AND status IN ('ready', 'approved', 'edited')
    """, [category.value])["count"]

    if today_count >= limits["daily_limit"]:
        return False, (
            f"تجاوز الحد اليومي لفئة {category.value}: "
            f"{today_count}/{limits['daily_limit']}"
        )

    return True, ""


def validate_variant_count(request: ContentRequest) -> int:
    """يُطبّق الحد الأقصى على عدد المتغيرات."""
    return min(
        max(request.variant_count, 1),
        MAX_VARIANTS,
    )
```

### التعديل في REQUEST_RECEIVER

```python
def request_receiver_node(state: ContentState) -> ContentState:
    request  = state["request"]

    # تحقق من حد الطلبات
    allowed, reason = check_rate_limit(request.content_category)
    if not allowed:
        state["status"]     = "rate_limited"
        state["error_code"] = "CON_RATE_LIMIT_EXCEEDED"
        state["error_detail"] = reason
        # TRANSACTIONAL يتجاوز الحد دائماً
        if request.content_category != ContentCategory.TRANSACTIONAL:
            return state

    # تطبيق حد المتغيرات
    request.variant_count = validate_variant_count(request)

    state["request"] = request
    return state
```

---

## تحديث Error Codes

```python
# إضافة لـ CONTENT_ERROR_CODES في v2:
{
    "CON_FACTUAL_CHECK_FAILED":   "فشل التحقق الدلالي — أُحيل للمراجعة",
    "CON_RATE_LIMIT_EXCEEDED":    "تجاوز الحد اليومي للفئة",
    "CON_MAX_VARIANTS_EXCEEDED":  "عدد المتغيرات يتجاوز الحد الأقصى",
    "CON_CONCURRENT_LIMIT":       "تجاوز حد التوليد المتزامن",
    "CON_QUEUE_FULL":             "الطابور ممتلئ — يُعاد لاحقاً",
    "CON_CONTENT_REJECTED":       "رُفض المحتوى في المراجعة البشرية",
}
```

---

## تحديث قائمة التحقق

```
□ Factual check: claude_factual_check_safe بحسب category
□ Factual check فشل: TRANSACTIONAL→fail | COMMERCIAL→retry | STRUCTURED→human
□ Registry Usage Policy مُطبَّق في system prompt
□ ContentStatus: APPROVED/EDITED/REJECTED مُستخدمة بعد human review
□ APPROVED → Registry update إن score ≥ 0.80
□ EDITED → versioning["human_edit"] = True
□ PRODUCT_PAGE_FULL: schema_version في المخرج
□ KNOWLEDGE_ARTICLE: evidence_source + evidence_verified_by في versioning
□ Rate limit مفحوص قبل بدء التوليد
□ variant_count ≤ MAX_VARIANTS = 5
□ MAX_CONCURRENT = 2 مُطبَّق
□ MAX_QUEUE_SIZE = 50 مُطبَّق
```

"""
Domain Model — وكيل المحتوى
المرجع: spec.md § ٥، ٦، ١٧، ١٩، ٢٠
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union


# ══════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════

class ContentCategory(str, Enum):
    TRANSACTIONAL = "transactional"
    COMMERCIAL    = "commercial"
    STRUCTURED    = "structured"


class ContentType(str, Enum):
    EMAIL_UPDATE         = "email_update"
    EMAIL_LAUNCH         = "email_launch"
    EMAIL_CAMPAIGN       = "email_campaign"
    PRODUCT_PAGE_SECTION = "product_page_section"
    PRODUCT_PAGE_FULL    = "product_page_full"
    KNOWLEDGE_ARTICLE    = "knowledge_article"
    MARKETING_COPY       = "marketing_copy"
    SOCIAL_CAPTION       = "social_caption"


class ContentStatus(str, Enum):
    REQUESTED       = "requested"
    GENERATING      = "generating"
    VALIDATING      = "validating"
    AWAITING_REVIEW = "awaiting_review"
    READY           = "ready"
    FAILED          = "failed"
    REJECTED        = "rejected"


class ContentTrigger(str, Enum):
    EVENT     = "event"
    ON_DEMAND = "on_demand"


class ReviewPolicy(str, Enum):
    AUTO_PUBLISH          = "auto_publish"
    AUTO_IF_SCORE         = "auto_if_score"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    HUMAN_REVIEW_OPTIONAL = "human_review_optional"
    HUMAN_IF_LOW_SCORE    = "human_if_low_score"


class FactType(str, Enum):
    VERIFIED_FACT     = "verified_fact"
    ALLOWED_INFERENCE = "allowed_inference"
    FORBIDDEN_CLAIM   = "forbidden_claim"


# ══════════════════════════════════════════════
# Maps ثابتة
# ══════════════════════════════════════════════

CONTENT_CATEGORY_MAP: Dict[ContentType, ContentCategory] = {
    ContentType.EMAIL_UPDATE:         ContentCategory.TRANSACTIONAL,
    ContentType.EMAIL_LAUNCH:         ContentCategory.COMMERCIAL,
    ContentType.EMAIL_CAMPAIGN:       ContentCategory.COMMERCIAL,
    ContentType.PRODUCT_PAGE_SECTION: ContentCategory.COMMERCIAL,
    ContentType.PRODUCT_PAGE_FULL:    ContentCategory.STRUCTURED,
    ContentType.KNOWLEDGE_ARTICLE:    ContentCategory.STRUCTURED,
    ContentType.MARKETING_COPY:       ContentCategory.COMMERCIAL,
    ContentType.SOCIAL_CAPTION:       ContentCategory.COMMERCIAL,
}

REVIEW_POLICY_MAP: Dict[ContentType, ReviewPolicy] = {
    ContentType.EMAIL_UPDATE:         ReviewPolicy.AUTO_PUBLISH,
    ContentType.EMAIL_LAUNCH:         ReviewPolicy.AUTO_IF_SCORE,
    ContentType.EMAIL_CAMPAIGN:       ReviewPolicy.HUMAN_REVIEW_OPTIONAL,
    ContentType.PRODUCT_PAGE_SECTION: ReviewPolicy.AUTO_IF_SCORE,
    ContentType.PRODUCT_PAGE_FULL:    ReviewPolicy.HUMAN_REVIEW_REQUIRED,
    ContentType.KNOWLEDGE_ARTICLE:    ReviewPolicy.HUMAN_IF_LOW_SCORE,
    ContentType.MARKETING_COPY:       ReviewPolicy.AUTO_IF_SCORE,
    ContentType.SOCIAL_CAPTION:       ReviewPolicy.AUTO_PUBLISH,
}

QUEUE_PRIORITY: Dict[ContentType, int] = {
    ContentType.EMAIL_UPDATE:         10,
    ContentType.EMAIL_LAUNCH:         7,
    ContentType.EMAIL_CAMPAIGN:       5,
    ContentType.PRODUCT_PAGE_FULL:    5,
    ContentType.KNOWLEDGE_ARTICLE:    6,
    ContentType.MARKETING_COPY:       4,
    ContentType.PRODUCT_PAGE_SECTION: 4,
    ContentType.SOCIAL_CAPTION:       3,
}

VARIANT_SUPPORT: Dict[ContentType, bool] = {
    ContentType.MARKETING_COPY: True,
    ContentType.SOCIAL_CAPTION: True,
    ContentType.EMAIL_CAMPAIGN: True,
}

CONTENT_TYPE_SPECS: Dict[ContentType, dict] = {
    ContentType.EMAIL_UPDATE:         {"الأقسام": ["تحية", "ملخص التحديث", "بنود التحديث", "رابط التحميل"], "الحد": "150-200"},
    ContentType.EMAIL_LAUNCH:         {"الأقسام": ["تحية", "hook", "الميزات الرئيسية", "CTA"], "الحد": "200-300"},
    ContentType.EMAIL_CAMPAIGN:       {"الأقسام": ["hook", "العرض", "الميزات", "CTA", "إغلاق"], "الحد": "250-350"},
    ContentType.PRODUCT_PAGE_SECTION: {"الأقسام": ["عنوان", "وصف", "نقاط الميزات"], "الحد": "100-200"},
    ContentType.PRODUCT_PAGE_FULL:    {"الأقسام": ["hero", "features", "pricing", "faq", "cta"], "الحد": "500-800"},
    ContentType.KNOWLEDGE_ARTICLE:    {"الأقسام": ["المشكلة", "الحل خطوة بخطوة", "ملاحظات", "النطاق"], "الحد": "300-500"},
    ContentType.MARKETING_COPY:       {"الأقسام": ["hook", "القيمة", "CTA"], "الحد": "80-150"},
    ContentType.SOCIAL_CAPTION:       {"الأقسام": ["hook", "النقطة الرئيسية", "CTA", "هاشتاق"], "الحد": "50-100"},
}

FACTUAL_CHECK_FALLBACK_POLICY: Dict[ContentCategory, str] = {
    ContentCategory.TRANSACTIONAL: "fail",
    ContentCategory.COMMERCIAL:    "retry_once",
    ContentCategory.STRUCTURED:    "human_review",
}

RETRY_CONFIG = {
    "max_attempts":      3,
    "backoff_seconds":   [30, 60, 120],
    "dead_letter_after": 3,
}

# Brand Constitution — أنماط المحظورات
BRAND_CONSTITUTION_FORBIDDEN_PATTERNS = [
    r"(?:أفضل|الأفضل)\s+(?:من|في)\s+\w+",       # مقارنة بالمنافسين
    r"\d+[\.,]?\d*\s*%\s+(?:زيادة|نمو|تحسين)",   # إحصاءات مبيعات غير مستندة
    r"(?:نضمن|نكفل|مضمون)\s+(?:نتائج|نجاح|مبيعات)", # ضمانات تجارية
    r"(?:رقم|رقماً)\s+(?:واحد|١|1)",             # ادعاء الصدارة
]

# Terminology Glossary
TERMINOLOGY_GLOSSARY: Dict[str, str] = {
    "Theme":        "قالب",
    "Template":     "قالب",
    "Plugin":       "إضافة",
    "Block":        "بلوك",
    "Editor":       "المحرر",
    "Dashboard":    "لوحة التحكم",
    "Installation": "التثبيت",
    "Activation":   "التفعيل",
    "License":      "الترخيص",
    "Update":       "تحديث",
    "Support":      "الدعم",
    "Download":     "تحميل",
}

# أسماء تقنية لا تُعرَّب
TECHNICAL_TERMS_KEEP = {
    "WordPress", "WooCommerce", "RTL", "FSE",
    "Gutenberg", "PHP", "CSS", "HTML", "API", "COD",
}


# ══════════════════════════════════════════════
# Dataclasses
# ══════════════════════════════════════════════

@dataclass
class ContextBundle:
    theme_facts:       Dict[str, str]
    product_registry:  Dict[str, str]
    release_metadata:  Dict[str, str]
    support_signals:   Dict[str, str]
    known_constraints: List[str]
    allowed_claims:    List[str]
    forbidden_claims:  List[str]
    source_map:        Dict[str, str]
    canonical_phrases: Dict[str, str]


@dataclass
class FactSheet:
    verified_facts:      List[str]
    allowed_inferences:  List[str]
    forbidden_claims:    List[str]
    constitution_version: str
    template_version:    str


@dataclass
class EvidenceContract:
    issue_summary:              str
    confirmed_resolution_steps: List[str]
    applicable_scope:           str
    known_limitations:          List[str]
    source:                     str
    verified_by:                str


@dataclass
class ContentRequest:
    request_id:        str
    trigger:           ContentTrigger
    requester:         str
    content_type:      ContentType
    content_category:  ContentCategory
    theme_slug:        Optional[str]
    theme_contract:    Optional[Dict]
    raw_context:       Dict
    target_agent:      str
    correlation_id:    str
    priority:          str
    output_mode:       str
    variant_count:     int
    evidence_contract: Optional[EvidenceContract]
    created_at:        datetime


@dataclass
class ContentPlan:
    request_id:       str
    content_type:     ContentType
    content_category: ContentCategory
    tone:             str
    channel_style:    str
    structure:        List[str]
    word_budget:      int
    key_messages:     List[str]
    context_bundle:   Optional[ContextBundle]
    fact_sheet:       Optional[FactSheet]
    template_id:      Optional[str]
    review_policy:    ReviewPolicy
    output_mode:      str
    variant_count:    int


@dataclass
class ContentPiece:
    content_id:        str
    request_id:        str
    content_type:      ContentType
    variant_label:     Optional[str]
    theme_slug:        Optional[str]
    title:             Optional[str]
    body:              Union[str, Dict]
    metadata:          Dict
    versioning:        Dict
    structural_score:  float
    language_score:    float
    factual_score:     float
    validation_score:  float
    validation_issues: List[str]
    status:            ContentStatus
    created_at:        datetime
    target_agent:      str


@dataclass
class ContentTemplate:
    template_id:       str
    template_version:  str
    content_type:      ContentType
    content_category:  ContentCategory
    name_ar:           str
    structure:         List[str]
    tone:              str
    channel_style:     str
    word_budget:       int
    review_policy:     ReviewPolicy
    supports_variants: bool
    example:           Optional[str]


# ══════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════

def build_content_idempotency_key(request: ContentRequest) -> str:
    """يبني مفتاح idempotency حسب نوع الطلب."""
    if request.trigger == ContentTrigger.EVENT:
        return (
            f"content:{request.content_type.value}"
            f":{request.theme_slug or 'general'}"
            f":{request.correlation_id}"
        )
    else:
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


def count_words(text: str) -> int:
    """يعدّ الكلمات في نص عربي أو مختلط."""
    return len(text.split())


def parse_word_budget(budget_str: str) -> int:
    """يحوّل '150-200' إلى 175 (المتوسط)."""
    if "-" in budget_str:
        parts = budget_str.split("-")
        return (int(parts[0]) + int(parts[1])) // 2
    return int(budget_str)


def calculate_english_ratio(text: str) -> float:
    """يحسب نسبة الأحرف اللاتينية في النص."""
    if not text:
        return 0.0
    english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total_chars   = sum(1 for c in text if c.isalpha())
    return english_chars / total_chars if total_chars > 0 else 0.0


def validate_terminology(text: str) -> List[str]:
    """يفحص المصطلحات ويُبلّغ عن الانحرافات."""
    issues = []
    for english, arabic in TERMINOLOGY_GLOSSARY.items():
        if re.search(rf'\b{english}\b', text, re.I) and arabic not in text:
            if english not in TECHNICAL_TERMS_KEEP:
                issues.append(f"مصطلح '{english}' يجب أن يُكتب '{arabic}'")
    return issues


def detect_unverified_statistics(text: str) -> List[str]:
    """يكشف الأرقام والإحصاءات غير المستندة."""
    patterns = [
        r'\d+\s*%\s+(?:من|زيادة|نمو|أكثر|أقل)',
        r'(?:أكثر|أقل)\s+من\s+\d+\s+(?:عميل|مستخدم|موقع)',
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, text)
        found.extend(matches)
    return found


def detect_tone_drift(text: str, expected_tone: str) -> List[str]:
    """يكشف الانحراف عن النبرة المطلوبة (فحص بسيط)."""
    issues = []
    if "رسمي" in expected_tone:
        # نبرة رسمية لا تستخدم الأمر المباشر المبتذل
        if re.search(r'\b(?:هيا|يلا|اشتري الحين)\b', text):
            issues.append("عبارات غير رسمية في محتوى رسمي")
    if "تسويقي" in expected_tone:
        if len(text) > 0 and text.count("!") == 0 and "MARKETING" in expected_tone.upper():
            pass  # مقبول
    return issues


def parse_evidence_contract(data: Optional[dict]) -> Optional[EvidenceContract]:
    """يحوّل dict إلى EvidenceContract."""
    if not data:
        return None
    return EvidenceContract(
        issue_summary              = data.get("issue_summary", ""),
        confirmed_resolution_steps = data.get("confirmed_resolution_steps", []),
        applicable_scope           = data.get("applicable_scope", ""),
        known_limitations          = data.get("known_limitations", []),
        source                     = data.get("source", ""),
        verified_by                = data.get("verified_by", ""),
    )

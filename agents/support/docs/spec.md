# وكيل الدعم — وكيل خدمة العملاء والمعرفة
## وثيقة المواصفات النهائية v3 — Support Agent

> تجمع v2 + تصحيحات ChatGPT المعتمدة + التصحيحات المعمارية الإضافية.
> المرجع التنفيذي الوحيد المعتمد لوكيل الدعم.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة
3. البنية التحتية
4. الكيانات الجوهرية — Domain Model الكامل
5. طبقتا التصنيف — Intent و Risk Flags
6. قاعدة المعرفة
7. معمارية الوكيل — ثلاثة Workflows
8. Workflow الأول — Message Processor
9. Workflow الثاني — Knowledge Builder
10. Workflow الثالث — Facebook Monitor
11. IDENTITY_RESOLVER — تحليل الهوية بالكيانات
12. COMBINED_CLASSIFIER — التصنيف المزدوج في طلب واحد
13. HARD_POLICY_GATE
14. RETRIEVAL_PLANNER
15. ANSWER_GENERATOR — JSON مع kb_disclaimer_rendered
16. ANSWER_VALIDATOR
17. CONFIDENCE_ROUTER
18. REPLY_SENDER
19. SAFE_REPLY_SENDER — مُفصَّل كاملاً
20. RESOLVED_TICKET_QUALIFIER
21. HUMAN_VERIFIED_KB_QUALIFIER
22. نظام التصعيد
23. Human Feedback Loop
24. TEXT_CLEANER
25. إدارة المقالات — Versioning + Deduplication
26. build_event Helper
27. Idempotency Strategy
28. Event Contract Schemas
29. أمان وخصوصية البيانات
30. Error Codes Catalog
31. بنية الـ State
32. متغيرات البيئة
33. دستور الوكيل
34. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل دعم ذكي يستقبل رسائل العملاء من البريد وFacebook Messenger، يُحلّل هويتهم بإشارات متعددة مقارَنة على entity_id، يُصنّف نواياهم ومخاطرهم في طبقتين مستقلتين بطلب API واحد، ويُجيب آلياً بما يعرفه مستشهداً بمصادر محددة، ويُصعّد ما لا يعرفه بأمانة — كل ذلك من قاعدة معرفة حية محروسة ببوابتَي جودة منفصلتَين للمصادر الآلية والبشرية.

### المبادئ غير القابلة للتفاوض

- **الصدق أولاً** — لا اختراع لإجابة عند الشك
- **الثقة تحكم التوجيه** — درجة محسوبة لا حدس
- **السياسات الصارمة فوق الثقة** — billing وlegal_threat يُصعَّدان دائماً
- **التعليقات العامة للبشر** — لا رد آلي على فيسبوك أبداً
- **قاعدة المعرفة محمية** — بوابتا جودة: QUALIFIER للآلي، HUMAN_VERIFIED للبشري
- **الخصوصية مصونة** — لا PII في Qdrant
- **الفشل الصامت ممنوع** — كل خطأ له كود ومُبلَّغ

---

## ٢. موقع الوكيل في المنظومة

```
وكيل المنصة → NEW_PRODUCT_LIVE → وكيل الدعم (يبني قاعدة المعرفة)
Commerce Consumer → LICENSE_ISSUED → وكيل الدعم (يُسجّل الترخيص)
HelpScout Webhook (جديد) → وكيل الدعم (Message Processor)
HelpScout Webhook (إغلاق) → وكيل الدعم (Human Feedback Loop)

وكيل الدعم →
  SUPPORT_TICKET_RESOLVED   → وكيل التحليل
  SUPPORT_TICKET_ESCALATED  → وكيل التحليل
  RECURRING_ISSUE_DETECTED  → وكيل التحليل
  KNOWLEDGE_BASE_UPDATED    → وكيل التحليل
  تصعيد + تنبيهات فيسبوك   → صاحب المشروع
```

---

## ٣. البنية التحتية

```
HelpScout  : Mailbox API + Webhooks + Docs API
Facebook   : Messenger (عبر HelpScout) + Comments (Graph API — تصنيف فقط)
Qdrant     : theme_docs + general_faqs + resolved_tickets
Resend     : إشعارات التصعيد + تنبيهات فيسبوك
Redis      : support_events (pub/sub)
PostgreSQL : execution_log + escalation_log + knowledge_log
```

---

## ٤. الكيانات الجوهرية — Domain Model الكامل

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────

class TicketIntent(Enum):
    """نية العميل — ماذا يريد؟"""
    TECHNICAL_SUPPORT      = "technical_support"
    LICENSE_QUESTION       = "license_question"
    SETUP_HELP             = "setup_help"
    CUSTOMIZATION_GUIDANCE = "customization_guidance"
    FEATURE_REQUEST        = "feature_request"
    BILLING_ISSUE          = "billing_issue"
    PRE_SALES_QUESTION     = "pre_sales_question"
    UNKNOWN                = "unknown"


class FacebookCommentIntent(Enum):
    """
    نية تعليق فيسبوك — مستقلة تماماً عن TicketIntent.
    "question" و"complaint" في التعليقات لا تقابل فئات نظام التذاكر.
    استخدام TicketIntent هنا سيكسر التنفيذ.
    """
    QUESTION  = "question"
    COMPLAINT = "complaint"
    PRAISE    = "praise"
    SPAM      = "spam"
    UNKNOWN   = "unknown"


class TicketStatus(Enum):
    """حالة التذكرة في دورة حياتها الكاملة"""
    OPEN      = "open"
    ANSWERED  = "answered"
    ESCALATED = "escalated"
    RESOLVED  = "resolved"
    CLOSED    = "closed"


class ResponseMode(Enum):
    FULL_ANSWER             = "full_answer"
    PARTIAL_WITH_DISCLAIMER = "partial_with_disclaimer"
    CLARIFYING_SAFE_REPLY   = "clarifying_safe_reply"
    ESCALATE_ONLY           = "escalate_only"


class EscalationReason(Enum):
    LOW_CONFIDENCE     = "low_confidence"
    BILLING_RELATED    = "billing_related"
    CODE_BUG_SUSPECTED = "code_bug_suspected"
    COMPLAINT          = "complaint"
    LEGAL_THREAT       = "legal_threat"
    REFUND_REQUEST     = "refund_request"
    REPEATED_ISSUE     = "repeated_issue"
    UNKNOWN_INTENT     = "unknown_intent"


class IdentityMatchType(Enum):
    EXACT_MATCH    = "exact_match"
    PROBABLE_MATCH = "probable_match"
    NO_MATCH       = "no_match"
    MULTIPLE_MATCH = "multiple_match"   # → لا ربط تلقائي أبداً


class CommentPriority(Enum):
    CRITICAL_PUBLIC_RISK = "critical_public_risk"   # "هذا المتجر نصاب" 🔴
    SALES_OPPORTUNITY    = "sales_opportunity"       # "هل يدعم الجوال؟" 🟢
    SUPPORT_QUESTION     = "support_question"        # سؤال تقني 🔵
    PRAISE               = "praise"                  # توثيق فقط
    SPAM                 = "spam"                    # توثيق فقط
    IGNORE               = "ignore"                  # تجاهل


class KBReadiness(Enum):
    NOT_BUILT = "not_built"
    BUILDING  = "building"
    READY     = "ready"
    FAILED    = "failed"


# ── Dataclasses ──────────────────────────────────

@dataclass
class RiskFlags:
    """مؤشرات المخاطرة — مستقلة عن Intent."""
    complaint:      bool = False
    angry:          bool = False
    bug_suspected:  bool = False
    refund_request: bool = False
    legal_threat:   bool = False

    def requires_immediate_escalation(self) -> bool:
        return (self.refund_request or self.legal_threat or
                (self.complaint and self.angry))


@dataclass
class SupportTicket:
    ticket_id:      str
    source:         str            # "email" | "messenger"
    customer_email: str
    customer_name:  Optional[str]
    subject:        str
    raw_body:       str            # النص الأصلي — لا يُعدَّل أبداً
    body:           str            # النظيف بعد TEXT_CLEANER
    language:       str            # "ar"|"en"|"mixed"|"dialect"
    theme_slug:     Optional[str]
    license_tier:   Optional[str]
    intent:         Optional[TicketIntent]
    risk_flags:     Optional[RiskFlags]
    status:         TicketStatus
    created_at:     datetime
    answered_at:    Optional[datetime]
    # key_issue يبقى في State — ليس هنا (استنتاج آلي لا بيانات مصدر)


@dataclass
class IdentityResolution:
    match_type:      IdentityMatchType
    entity_id:       Optional[str]   # customer_id أو license_id — مفتاح المقارنة
    license_info:    Optional[Dict]
    theme_slug:      Optional[str]
    license_tier:    Optional[str]
    license_status:  Optional[str]
    match_signals:   List[str]       # الإشارات التي استُخدمت
    confidence:      float


@dataclass
class KnowledgeArticle:
    article_id:    str
    theme_slug:    Optional[str]
    article_type:  str    # installation|features|woo|cod|faq|presales|whats_new
    version:       str
    supersedes:    Optional[str]   # article_id القديم الذي يحل محله
    is_latest:     bool
    title_ar:      str
    content_ar:    str
    category:      str
    embedding:     List[float]
    source:        str    # auto_generated|manual|resolved_ticket|human_verified
    created_at:    datetime
    updated_at:    datetime


@dataclass
class FacebookComment:
    """
    مستقل عن SupportTicket.
    يستخدم FacebookCommentIntent لا TicketIntent.
    """
    comment_id:       str
    post_id:          str
    author_name:      str
    content:          str
    priority:         CommentPriority
    intent:           FacebookCommentIntent   # ← enum مستقل
    sentiment:        str
    requires_action:  bool
    reply_suggestion: Optional[str]           # اقتراح رد لصاحب المشروع
    created_at:       datetime
    notified_at:      Optional[datetime]


@dataclass
class AnswerCitation:
    source_id:        str
    title_ar:         str
    evidence_snippet: str   # أقل من 100 حرف


@dataclass
class EscalationRecord:
    escalation_id:       str
    ticket_id:           str
    reason:              EscalationReason
    key_issue:           str
    suggested_answer:    Optional[str]
    escalated_at:        datetime
    resolved_at:         Optional[datetime]
    resolution:          Optional[str]
    was_answer_correct:  Optional[bool]   # من Human Feedback Loop
```

---

## ٥. طبقتا التصنيف — Intent و Risk Flags

```python
HARD_ROUTING_RULES = {
    "billing_keywords": [
        "استرداد", "استعادة المبلغ", "إلغاء", "دفع", "بطاقة", "فاتورة",
        "refund", "cancel", "payment", "charge",
    ],
    "legal_threat_keywords": [
        "محامي", "قضية", "بلاغ", "احتيال", "نصاب",
        "lawyer", "sue", "fraud", "scam", "legal",
    ],
}

def apply_hard_routing(
    text:   str,
    intent: TicketIntent,
    risk:   RiskFlags,
) -> tuple[TicketIntent, RiskFlags]:
    """تُطبَّق بعد COMBINED_CLASSIFIER — تتجاوز نتيجته."""
    text_lower = text.lower()

    if any(kw in text_lower for kw in HARD_ROUTING_RULES["billing_keywords"]):
        intent              = TicketIntent.BILLING_ISSUE
        risk.refund_request = True

    if any(kw in text_lower for kw in HARD_ROUTING_RULES["legal_threat_keywords"]):
        risk.legal_threat = True

    return intent, risk
```

---

## ٦. قاعدة المعرفة

```
ثلاثة مصادر + بوابتا جودة:

مصدر ١: توثيق آلي من THEME_CONTRACT
  ← بوابة: THEME_BUILD_PRECHECK (idempotency)

مصدر ٢: تذاكر محلولة بثقة عالية
  ← بوابة: RESOLVED_TICKET_QUALIFIER (7 شروط)

مصدر ٣: حلول بشرية من Feedback Loop
  ← بوابة: HUMAN_VERIFIED_KB_QUALIFIER (5 شروط)
```

```python
def get_kb_readiness(theme_slug: str) -> KBReadiness:
    record = knowledge_log.get(theme_slug)
    if not record:
        return KBReadiness.NOT_BUILT
    return KBReadiness(record["status"])

def get_kb_fallback_message() -> str:
    return (
        "هذا القالب جديد وجاري بناء توثيقه. "
        "للمساعدة الفورية يرجى وصف مشكلتك بالتفصيل."
    )
```

---

## ٧. معمارية الوكيل — ثلاثة Workflows

```
Workflow 1: Message Processor  — خطي لكل تذكرة
Workflow 2: Knowledge Builder  — عند NEW_PRODUCT_LIVE أو THEME_UPDATED_LIVE
Workflow 3: Facebook Monitor   — دائم كل 15 دقيقة
```

---

## ٨. Workflow الأول — Message Processor

```
[MESSAGE_RECEIVER]
      ↓
[IDEMPOTENCY_CHECK] ──► مُعالَج → END
      ↓
[TEXT_CLEANER]
      ↓
[LANGUAGE_DETECTOR]
      ↓
[IDENTITY_RESOLVER]
      ↓
[CUSTOMER_ENRICHER]
      ↓
[COMBINED_CLASSIFIER]   ← Intent + RiskFlags في طلب واحد
      ↓
[HARD_ROUTING_RULES]    ← تُطبَّق فوراً
      ↓
[HARD_POLICY_GATE]
      ├── escalate_immediate ──────────────────► [ESCALATION_HANDLER] → END
      ├── feature_request   ──────────────────► [FEATURE_RECORDER] → END
      ↓
[RETRIEVAL_PLANNER]
      ↓
[RAG_RETRIEVER]
      ↓
[ANSWER_GENERATOR]      ← JSON + kb_disclaimer_rendered
      ↓
[ANSWER_VALIDATOR]
      ↓
[CONFIDENCE_ROUTER]
  HIGH   → [REPLY_SENDER] → [RESOLVED_TICKET_QUALIFIER] → END
  MEDIUM → [SAFE_REPLY_SENDER] → [SOFT_ESCALATION] → END
  LOW    → [ESCALATION_HANDLER] → END
```

---

## ٩. Workflow الثاني — Knowledge Builder

```
[KB_ENTRY]
      ↓
[THEME_BUILD_PRECHECK]   ← idempotency: هذا الإصدار مبني؟
      ↓
[CONTRACT_PARSER]
      ↓
[INSTALLATION_WRITER] [FEATURES_WRITER] [WOO_WRITER] [COD_WRITER]
[FAQ_GENERATOR] [PRESALES_WRITER] [WHATS_NEW_WRITER]*
      ↓
[DEDUP_CHECKER]          ← similarity < 0.92
      ↓
[EMBEDDER]               ← Qdrant upsert مع versioning
      ↓
[HELPSCOUT_PUBLISHER]    ← HelpScout Docs API
      ↓
[KB_STATUS_RECORDER]     ← status = "ready"
      ↓
[KB_ANNOUNCER]           ← KNOWLEDGE_BASE_UPDATED على Redis
      ↓
     END

* WHATS_NEW_WRITER: عند THEME_UPDATED_LIVE فقط
```

---

## ١٠. Workflow الثالث — Facebook Monitor

```python
FACEBOOK_MONITOR_INTERVAL_MINUTES = 15
# القيد الجوهري: لا رد آلي على أي تعليق عام أبداً

PRIORITY_NOTIFICATION_MAP = {
    CommentPriority.CRITICAL_PUBLIC_RISK: "🔴 عاجل — خطر على السمعة",
    CommentPriority.SALES_OPPORTUNITY:    "🟢 فرصة بيع",
    CommentPriority.SUPPORT_QUESTION:     "🔵 سؤال دعم",
    # PRAISE + SPAM → توثيق فقط، لا تنبيه
    # IGNORE → تجاهل تام
}
```

---

## ١١. IDENTITY_RESOLVER — تحليل الهوية بالكيانات

```python
"""
المبدأ الجوهري:
المقارنة على entity_id (customer_id / license_id) لا على عدد المصادر.

تعدد الإشارات ≠ تعدد الكيانات:
بريد + رابط موقع + اسم = 3 إشارات → entity_id واحد → EXACT_MATCH

مصدران يعودان لـ entity_id مختلفَين → MULTIPLE_MATCH
"""

def resolve_identity_by_entity(signals: dict) -> IdentityResolution:
    matches = []

    # مفتاح الترخيص — الأدق دائماً
    if signals.get("license_key"):
        result = ls_client.validate_license(signals["license_key"])
        if result:
            matches.append({
                "entity_id":  result["license_key"],
                "source":     "license_key",
                "confidence": 1.0,
                "data":       result,
            })

    # رقم الطلب
    if signals.get("order_id"):
        result = ls_client.find_order(signals["order_id"])
        if result:
            matches.append({
                "entity_id":  result["customer_id"],
                "source":     "order_id",
                "confidence": 0.95,
                "data":       result,
            })

    # البريد الإلكتروني
    if signals.get("customer_email"):
        results = ls_client.find_licenses_by_email(signals["customer_email"])
        for r in (results or []):
            matches.append({
                "entity_id":  r["customer_id"],
                "source":     "email",
                "confidence": 0.80,
                "data":       r,
            })

    if not matches:
        return IdentityResolution(
            match_type=IdentityMatchType.NO_MATCH,
            entity_id=None, license_info=None, theme_slug=None,
            license_tier=None, license_status=None,
            match_signals=[], confidence=0.0,
        )

    # تحقق على entity_id — ليس عدد المصادر
    unique_entities = set(m["entity_id"] for m in matches)

    if len(unique_entities) > 1:
        return IdentityResolution(
            match_type=IdentityMatchType.MULTIPLE_MATCH,
            entity_id=None, license_info=None, theme_slug=None,
            license_tier=None, license_status=None,
            match_signals=list(signals.keys()), confidence=0.0,
        )

    best = max(matches, key=lambda m: m["confidence"])
    data = best["data"]

    return IdentityResolution(
        match_type     = (IdentityMatchType.EXACT_MATCH
                          if best["confidence"] >= 0.90
                          else IdentityMatchType.PROBABLE_MATCH),
        entity_id      = best["entity_id"],
        license_info   = data,
        theme_slug     = get_theme_slug_by_product(data.get("product_id")),
        license_tier   = detect_tier(data.get("variant_id")),
        license_status = data.get("status"),
        match_signals  = [m["source"] for m in matches],
        confidence     = best["confidence"],
    )
```

---

## ١٢. COMBINED_CLASSIFIER — التصنيف المزدوج في طلب واحد

```python
"""
لماذا طلب واحد لا طلبان؟
- تكلفة API مضاعفة في طلبين
- فرصة تعارض النتائج
- السياق الواحد ينتج تصنيفاً أكثر اتساقاً
"""

COMBINED_CLASSIFIER_SYSTEM = """
صنّف نية رسالة دعم قوالب WordPress العربية ومؤشرات مخاطرتها.
أرجع JSON فقط.
"""

def combined_classifier_node(state: SupportState) -> SupportState:
    ticket = state["ticket"]

    response = claude_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = 300,
        system     = COMBINED_CLASSIFIER_SYSTEM,
        messages   = [{"role": "user", "content": f"""
الموضوع: {ticket.subject}
الرسالة: {ticket.body}
لديه ترخيص: {state['customer_context'].get('has_license', False)}
القالب: {ticket.theme_slug or 'غير محدد'}

{{
    "intent": "technical_support|license_question|setup_help|customization_guidance|feature_request|billing_issue|pre_sales_question|unknown",
    "intent_confidence": 0.0-1.0,
    "key_issue": "جملة واحدة بالعربية",
    "theme_mentioned": null,
    "license_key_mentioned": null,
    "order_id_mentioned": null,
    "site_url_mentioned": null,
    "language": "ar|en|mixed|dialect",
    "risk_flags": {{
        "complaint": false,
        "angry": false,
        "bug_suspected": false,
        "refund_request": false,
        "legal_threat": false
    }}
}}
"""}],
    ).content[0].text

    result = json.loads(response)

    ticket.intent     = TicketIntent(result["intent"])
    ticket.risk_flags = RiskFlags(**result["risk_flags"])
    ticket.language   = result.get("language", "ar")

    state["key_issue"] = result["key_issue"]   # State — ليس Ticket

    # تطبيق القواعد الصارمة فوراً
    ticket.intent, ticket.risk_flags = apply_hard_routing(
        ticket.body, ticket.intent, ticket.risk_flags
    )

    # إشارات هوية إضافية اكتشفها المصنّف
    if result.get("license_key_mentioned"):
        state["discovered_license_key"] = result["license_key_mentioned"]
    if result.get("order_id_mentioned"):
        state["discovered_order_id"] = result["order_id_mentioned"]

    return state
```

---

## ١٣. HARD_POLICY_GATE

```python
def hard_policy_gate_node(state: SupportState) -> SupportState:
    intent     = state["ticket"].intent
    risk_flags = state["ticket"].risk_flags

    if intent == TicketIntent.BILLING_ISSUE:
        state["escalation_reason"] = EscalationReason.BILLING_RELATED
        state["route"]             = "escalate_immediate"
        return state

    if risk_flags.refund_request:
        state["escalation_reason"] = EscalationReason.REFUND_REQUEST
        state["route"]             = "escalate_immediate"
        return state

    if risk_flags.legal_threat:
        state["escalation_reason"] = EscalationReason.LEGAL_THREAT
        state["route"]             = "escalate_immediate"
        return state

    if intent == TicketIntent.FEATURE_REQUEST:
        state["route"] = "feature_request"
        return state

    state["route"] = "proceed"
    return state
```

---

## ١٤. RETRIEVAL_PLANNER

```python
RETRIEVAL_PLANS = {
    TicketIntent.TECHNICAL_SUPPORT: {
        "search_order":       ["theme_docs", "resolved_tickets", "general_faqs"],
        "allowed_categories": ["installation", "configuration", "faq"],
    },
    TicketIntent.LICENSE_QUESTION: {
        "search_order":       ["general_faqs", "theme_docs"],
        "allowed_categories": ["license", "faq"],
        # لا resolved_tickets — سؤال ترخيص لا يأخذ وزناً من التذاكر التقنية
    },
    TicketIntent.SETUP_HELP: {
        "search_order":       ["theme_docs", "general_faqs"],
        "allowed_categories": ["installation", "configuration"],
    },
    TicketIntent.CUSTOMIZATION_GUIDANCE: {
        "search_order":       ["theme_docs", "general_faqs"],
        "allowed_categories": ["configuration", "faq"],
    },
    TicketIntent.PRE_SALES_QUESTION: {
        "search_order":       ["general_faqs", "theme_docs"],
        "allowed_categories": ["pre_sales", "faq"],
        # لا resolved_tickets لأسئلة ما قبل الشراء
    },
}
```

---

## ١٥. ANSWER_GENERATOR — JSON مع kb_disclaimer_rendered

```python
ANSWER_GENERATOR_SYSTEM = """
أنت وكيل دعم متخصص في قوالب WordPress العربية.
١. لا تُجيب بما لا تجده في التوثيق
٢. كل ادعاء مستند لـ source_id محدد
٣. لا تعطِ وعوداً بتخصيصات غير موثقة
٤. أرجع JSON فقط
"""

# مخطط المخرج:
ANSWER_OUTPUT_SCHEMA = """
{
    "answer": "الرد بالعربية",
    "confidence": 0.0-1.0,
    "response_mode": "full_answer|partial_with_disclaimer|clarifying_safe_reply|escalate_only",
    "source_ids": ["article_id"],
    "evidence_snippets": ["جزء النص"],
    "unsupported_claims_detected": false,
    "kb_disclaimer_rendered": false,
    "follow_up_needed": false,
    "bug_suspected": false
}

ملاحظة: إن كانت قاعدة المعرفة غير جاهزة أو التوثيق غير كافٍ،
اجعل kb_disclaimer_rendered=true وأشر للمتابعة في الإجابة.
"""
```

---

## ١٦. ANSWER_VALIDATOR

```python
def answer_validator_node(state: SupportState) -> SupportState:
    confidence = state.get("answer_confidence", 0.0)
    issues     = []

    if state.get("unsupported_claims"):
        issues.append("unsupported_claims")
        state["answer_confidence"] = min(confidence, 0.55)

    if is_tone_unsafe(state.get("generated_answer", "")):
        issues.append("unsafe_tone")
        state["answer_confidence"] = 0.0

    if contains_policy_breach(state.get("generated_answer", "")):
        issues.append("policy_breach")
        state["answer_confidence"] = 0.0

    if (confidence >= 0.75 and
        not state.get("answer_citations") and
        not state.get("kb_not_ready")):
        issues.append("high_confidence_no_citations")
        state["answer_confidence"] = min(confidence, 0.59)

    # يُتحقَّق من field المنظم — لا من عبارات حرفية
    if state.get("kb_not_ready") and not state.get("kb_disclaimer_rendered"):
        issues.append("missing_kb_disclaimer")
        state["answer_confidence"] = min(confidence, 0.50)

    state["validation_issues"] = issues
    return state
```

---

## ١٧. CONFIDENCE_ROUTER

```python
CONFIDENCE_THRESHOLDS = {"high": 0.85, "medium": 0.60}

def confidence_router(state: SupportState) -> str:
    confidence    = state["answer_confidence"]
    risk_flags    = state["ticket"].risk_flags
    response_mode = state.get("response_mode", ResponseMode.FULL_ANSWER)

    if risk_flags.requires_immediate_escalation(): return "escalate"
    if state.get("bug_suspected"):                 return "escalate"
    if response_mode == ResponseMode.ESCALATE_ONLY: return "escalate"

    if confidence >= CONFIDENCE_THRESHOLDS["high"]:   return "reply_direct"
    if confidence >= CONFIDENCE_THRESHOLDS["medium"]:  return "reply_with_soft_escalation"
    return "escalate"
```

---

## ١٨. REPLY_SENDER

```python
def reply_sender_node(state: SupportState) -> SupportState:
    helpscout_client.reply_to_conversation(
        conversation_id = state["ticket"].ticket_id,
        body            = state["generated_answer"] + f"\n\n---\nفريق دعم قوالب عربية",
        status          = "closed" if not state["follow_up_needed"] else "active",
    )

    state["ticket"].status  = TicketStatus.ANSWERED
    state["route_taken"]    = "reply_direct"   # يُستخدم في QUALIFIER

    publish_support_event("SUPPORT_TICKET_RESOLVED", {
        "ticket_id":     state["ticket"].ticket_id,
        "intent":        state["ticket"].intent.value if state["ticket"].intent else "unknown",
        "confidence":    state["answer_confidence"],
        "response_mode": state["response_mode"].value if state["response_mode"] else "full_answer",
        "theme_slug":    state["ticket"].theme_slug,
        "kb_indexed":    False,
    }, state["idempotency_key"])

    return state
```

---

## ١٩. SAFE_REPLY_SENDER — مُفصَّل كاملاً

```python
"""
يختلف عن REPLY_SENDER في أربعة محاور:
١. يُضيف disclaimer صريحاً للعميل
٢. يترك التذكرة active لا closed
٣. يُضيف ملاحظة داخلية للمراجعة البشرية
٤. لا يُرسل للـ RESOLVED_TICKET_QUALIFIER
   (التذكرة لم تُغلق بثقة كاملة — route_taken ≠ "reply_direct")
"""

def safe_reply_sender_node(state: SupportState) -> SupportState:
    answer        = state["generated_answer"]
    response_mode = state.get("response_mode", ResponseMode.PARTIAL_WITH_DISCLAIMER)

    if response_mode == ResponseMode.PARTIAL_WITH_DISCLAIMER:
        full_reply = (
            f"{answer}\n\n---\n"
            "ملاحظة: هذه الإجابة قد تكون جزئية. "
            "سيتولى فريق الدعم مراجعة تذكرتك وإكمال المساعدة."
        )
    elif response_mode == ResponseMode.CLARIFYING_SAFE_REPLY:
        full_reply = (
            f"{answer}\n\n"
            "لمساعدتك بشكل أفضل، هل يمكنك تزويدنا بمزيد من التفاصيل؟"
        )
    else:
        full_reply = answer

    # الإرسال — التذكرة تبقى active
    helpscout_client.reply_to_conversation(
        conversation_id = state["ticket"].ticket_id,
        body            = full_reply,
        status          = "active",
    )

    # ملاحظة داخلية لصاحب المشروع
    helpscout_client.add_note(
        conversation_id = state["ticket"].ticket_id,
        body = (
            f"🟡 رد آلي بثقة متوسطة ({state['answer_confidence']:.0%})\n"
            f"الوضع: {response_mode.value}\n"
            f"المصادر: {[c.source_id for c in state.get('answer_citations', [])]}\n"
            f"يُنصح بالمراجعة البشرية لإكمال الحل."
        ),
    )

    state["ticket"].status = TicketStatus.ANSWERED
    state["route_taken"]   = "reply_with_soft_escalation"
    # لا إرسال لـ QUALIFIER
    return state


def soft_escalation_node(state: SupportState) -> SupportState:
    """حدث داخلي فقط — لا بريد لصاحب المشروع."""
    publish_support_event("SUPPORT_TICKET_SOFT_ESCALATED", {
        "ticket_id":  state["ticket"].ticket_id,
        "confidence": state["answer_confidence"],
        "theme_slug": state["ticket"].theme_slug,
    }, state["idempotency_key"])
    return state
```

---

## ٢٠. RESOLVED_TICKET_QUALIFIER

```python
"""
يُطبَّق فقط في مسار reply_direct.
SAFE_REPLY_SENDER لا يُرسل هنا.
التحقق على route_taken — أوضح من ticket.status.
"""

QUALIFIER_CRITERIA = {
    "min_answer_confidence":    0.90,
    "min_retrieval_score":      0.80,
    "max_similarity_threshold": 0.88,
}

def resolved_ticket_qualifier_node(state: SupportState) -> SupportState:
    # فحص مسار التوجيه — لا ticket.status
    if state.get("route_taken") != "reply_direct":
        return state

    decision = _evaluate(state)
    state["kb_indexing_decision"] = decision

    if decision == "insert":
        index_resolved_ticket(
            question   = state["ticket"].body,
            answer     = state["generated_answer"],
            theme_slug = state["ticket"].theme_slug,
            citations  = state["answer_citations"],
        )
    elif decision == "queue_for_review":
        kb_review_queue.add({
            "ticket_id": state["ticket"].ticket_id,
            "question":  state["ticket"].body,
            "answer":    state["generated_answer"],
            "reason":    "يحتاج مراجعة بشرية",
        })

    return state


def _evaluate(state: SupportState) -> str:
    if state["answer_confidence"]  < QUALIFIER_CRITERIA["min_answer_confidence"]:  return "skip"
    if state.get("retrieval_score", 0) < QUALIFIER_CRITERIA["min_retrieval_score"]: return "skip"
    if state["ticket"].risk_flags.complaint or state.get("follow_up_needed"):       return "skip"
    if contains_personal_data(state["generated_answer"]):                           return "skip"
    similarity = check_similarity(state["ticket"].body, state["ticket"].theme_slug)
    if similarity > QUALIFIER_CRITERIA["max_similarity_threshold"]:                 return "skip"
    if state.get("unsupported_claims"):                                             return "queue_for_review"
    return "insert"
```

---

## ٢١. HUMAN_VERIFIED_KB_QUALIFIER

```python
"""
ليس كل حل بشري صالح لإعادة الاستخدام.
بعضها ظرفي، أو قصير جداً، أو يعتمد على سياق غير ظاهر.
"""

HUMAN_QUALIFIER_CRITERIA = {
    "min_length_chars": 150,
    "max_length_chars": 2000,
}

def human_verified_kb_qualifier(
    human_reply: str,
    key_issue:   str,
    theme_slug:  Optional[str],
) -> str:
    """يُرجع: insert | queue | skip"""

    if len(human_reply.strip()) < HUMAN_QUALIFIER_CRITERIA["min_length_chars"]:
        return "skip"

    if len(human_reply) > HUMAN_QUALIFIER_CRITERIA["max_length_chars"]:
        return "queue"   # طويل — يحتاج تلخيصاً

    if contains_personal_data(human_reply):
        return "skip"

    # ليس مجرد "تم الحل"
    transactional = ["تم الحل", "مشكور", "حللت", "ok", "done", "fixed"]
    if any(p in human_reply.lower() for p in transactional):
        return "skip"

    # تقييم قابلية التعميم
    score = assess_generalizability(human_reply, key_issue)
    if score < 0.70:
        return "skip"

    return "insert"


def assess_generalizability(answer: str, key_issue: str) -> float:
    result = claude_client.messages.create(
        model      = "claude-sonnet-4-20250514",
        max_tokens = 60,
        system     = "قيّم قابلية تعميم هذا الحل. أرجع JSON: {\"score\": 0.0-1.0}",
        messages   = [{"role": "user", "content":
                        f"المشكلة: {key_issue}\nالحل: {answer}"}],
    ).content[0].text
    return json.loads(result).get("score", 0.0)
```

---

## ٢٢. نظام التصعيد

```python
def escalation_handler_node(state: SupportState) -> SupportState:
    ticket    = state["ticket"]
    reason    = state.get("escalation_reason") or determine_reason(state)

    # key_issue له fallback — قد يكون فارغاً عند التصعيد المبكر من HARD_POLICY_GATE
    key_issue = state.get("key_issue") or ticket.subject or "غير محدد"

    helpscout_client.add_note(
        conversation_id = ticket.ticket_id,
        body = (
            f"🔴 تصعيد آلي — السبب: {reason.value}\n\n"
            f"المشكلة: {key_issue}\n"
            f"الثقة: {state.get('answer_confidence', 0):.0%}\n"
            f"القالب: {ticket.theme_slug or 'غير محدد'}\n"
            f"مؤشرات المخاطرة: {vars(ticket.risk_flags) if ticket.risk_flags else {}}\n\n"
            f"الإجابة المقترحة:\n{state.get('generated_answer', 'لا توجد')}"
        ),
    )

    helpscout_client.update_conversation_status(
        conversation_id = ticket.ticket_id, status = "pending"
    )

    send_escalation_notification(ticket, reason, key_issue, state)

    escalation_log.record(EscalationRecord(
        escalation_id    = str(uuid.uuid4()),
        ticket_id        = ticket.ticket_id,
        reason           = reason,
        key_issue        = key_issue,
        suggested_answer = state.get("generated_answer"),
        escalated_at     = datetime.utcnow(),
        was_answer_correct = None,
    ))

    check_recurring_issues(state, key_issue)

    publish_support_event("SUPPORT_TICKET_ESCALATED", {
        "ticket_id":  ticket.ticket_id,
        "reason":     reason.value,
        "intent":     ticket.intent.value if ticket.intent else "unknown",
        "theme_slug": ticket.theme_slug,
    }, state["idempotency_key"])

    ticket.status = TicketStatus.ESCALATED
    return state


def check_recurring_issues(state: SupportState, key_issue: str) -> None:
    """
    key_issue كمعامل صريح — لا يعتمد على state["key_issue"]
    لأنه قد يكون فارغاً عند التصعيد المبكر من HARD_POLICY_GATE.
    """
    if not key_issue or key_issue == "غير محدد":
        return

    count = escalation_log.count_similar(
        key_issue    = key_issue,
        theme_slug   = state["ticket"].theme_slug,
        within_hours = 48,
    )

    if count >= 3:
        publish_support_event("RECURRING_ISSUE_DETECTED", {
            "theme_slug":   state["ticket"].theme_slug,
            "issue":        key_issue,
            "count":        count,
            "within_hours": 48,
        }, state["idempotency_key"])
```

---

## ٢٣. Human Feedback Loop

```python
"""
المُشغِّل: HelpScout Webhook "conversation.status-changed" (status=closed)
يُطلق عند إغلاق أي تذكرة — بما فيها المصعَّدة.
هذا يُجيب على: كيف يعود قرار البشر للنظام؟
"""

def human_feedback_processor(webhook: dict) -> None:
    if webhook.get("event") != "conversation.status-changed": return
    if webhook["data"].get("status") != "closed":             return

    ticket_id  = str(webhook["data"]["id"])
    escalation = escalation_log.get_by_ticket(ticket_id)
    if not escalation:
        return

    human_reply = helpscout_client.get_last_human_reply(ticket_id)
    if not human_reply:
        return

    feedback = analyze_feedback(
        agent_answer = escalation.suggested_answer,
        human_answer = human_reply,
        key_issue    = escalation.key_issue,
    )

    escalation_log.update_feedback(
        escalation_id      = escalation.escalation_id,
        was_answer_correct = feedback["was_agent_correct"],
        resolution         = human_reply,
        resolved_at        = datetime.utcnow(),
    )

    if not feedback["was_agent_correct"]:
        kb_review_queue.mark_rejected(ticket_id)
        return

    if feedback["human_answer_generalizable"]:
        qualification = human_verified_kb_qualifier(
            human_reply = human_reply,
            key_issue   = escalation.key_issue,
            theme_slug  = get_theme_slug_from_ticket(ticket_id),
        )

        if qualification == "insert":
            index_human_verified_answer(
                question   = escalation.key_issue,
                answer     = human_reply,
                theme_slug = get_theme_slug_from_ticket(ticket_id),
            )
        elif qualification == "queue":
            kb_review_queue.add({
                "ticket_id": ticket_id,
                "question":  escalation.key_issue,
                "answer":    human_reply,
                "source":    "human_verified",
                "reason":    "يحتاج تلخيصاً قبل الإدراج",
            })
```

---

## ٢٤. TEXT_CLEANER

```python
def text_cleaner_node(state: SupportState) -> SupportState:
    """
    last_message["body"] من HelpScout يحتوي HTML + ردود مقتبسة + توقيعات.
    النص الملوث يُفسد التصنيف والاسترجاع.
    """
    clean = BeautifulSoup(state["ticket"].raw_body, "html.parser").get_text()

    # إزالة تاريخ الردود
    for p in [r"On .+? wrote:.*", r"في \d{1,2}/\d{1,2}/\d{4}.+? كتب:.*",
               r"-----Original Message-----.*", r"From:.*\nSent:.*\nTo:.*"]:
        clean = re.sub(p, "", clean, flags=re.DOTALL | re.MULTILINE)

    # إزالة التوقيعات
    for p in [r"--\s*\n.*", r"Sent from my.*", r"تم الإرسال من.*"]:
        clean = re.sub(p, "", clean, flags=re.DOTALL)

    # تطبيع العربية
    for old, new in {"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"}.items():
        clean = clean.replace(old, new)

    state["ticket"].body = re.sub(r"\s+", " ", clean).strip()
    return state
```

---

## ٢٥. إدارة المقالات — Versioning + Deduplication

```python
def update_article_for_new_version(
    theme_slug: str, new_version: str,
    article_type: str, new_content: str,
) -> None:
    """
    المقالة القديمة: is_latest=False, superseded=True
    المقالة الجديدة: supersedes=article_id_القديم, is_latest=True
    لا حذف — التاريخ محفوظ دائماً.
    """
    old = knowledge_store.get_latest(theme_slug, article_type)
    if old:
        knowledge_store.mark_superseded(old["article_id"])

    qdrant_client.upsert("theme_docs", KnowledgeArticle(
        article_id   = f"{theme_slug}_{article_type}_{new_version}",
        theme_slug   = theme_slug,
        article_type = article_type,
        version      = new_version,
        supersedes   = old["article_id"] if old else None,
        is_latest    = True,
        title_ar     = build_title(article_type, theme_slug),
        content_ar   = new_content,
        category     = map_type_to_category(article_type),
        embedding    = embed(new_content),
        source       = "auto_generated",
        created_at   = datetime.utcnow(),
        updated_at   = datetime.utcnow(),
    ))
```

---

## ٢٦. build_event Helper — الصيغة الموحدة

```python
"""
كل أحداث المنظومة تتبع هذه الصيغة.
مُعرَّفة أيضاً في وكيل المنصة — نفس الـ helper.
"""

def build_event(
    event_type:     str,
    source:         str,
    correlation_id: str,
    data:           dict,
    schema_version: str = "1.0",
) -> dict:
    return {
        "event_id":       str(uuid.uuid4()),
        "event_type":     event_type,
        "event_version":  schema_version,
        "source":         source,
        "occurred_at":    datetime.utcnow().isoformat() + "Z",
        "correlation_id": correlation_id,
        "data":           data,
    }

def publish_support_event(event_type: str, data: dict,
                           correlation_id: str) -> None:
    redis.publish("support_events", json.dumps(
        build_event(event_type, "support_agent", correlation_id, data)
    ))

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
```

---

## ٢٧. Idempotency Strategy

```python
IDEMPOTENCY_KEYS = {
    "ticket_processing":   "ticket:{ticket_id}",
    "knowledge_building":  "kb:{theme_slug}:{version}",
    "fb_comment":          "fb_comment:{comment_id}",
    "feedback_processing": "feedback:{ticket_id}",
}
```

---

## ٢٨. Event Contract Schemas

```json
SUPPORT_TICKET_RESOLVED: {
  "event_type": "SUPPORT_TICKET_RESOLVED", "event_version": "1.0",
  "source": "support_agent",
  "data": {"ticket_id": "...", "intent": "technical_support",
           "confidence": 0.92, "response_mode": "full_answer",
           "theme_slug": "restaurant_modern", "kb_indexed": true}
}

SUPPORT_TICKET_ESCALATED: {
  "event_type": "SUPPORT_TICKET_ESCALATED", "event_version": "1.0",
  "data": {"ticket_id": "...", "reason": "billing_related",
           "intent": "billing_issue", "theme_slug": "restaurant_modern"}
}

RECURRING_ISSUE_DETECTED: {
  "event_type": "RECURRING_ISSUE_DETECTED", "event_version": "1.0",
  "data": {"theme_slug": "restaurant_modern",
           "issue": "لا تظهر قائمة الطعام",
           "count": 4, "within_hours": 48}
}

KNOWLEDGE_BASE_UPDATED: {
  "event_type": "KNOWLEDGE_BASE_UPDATED", "event_version": "1.0",
  "data": {"theme_slug": "restaurant_modern",
           "articles_added": 6, "version": "20250316-0001"}
}
```

---

## ٢٩. أمان وخصوصية البيانات

```python
SECURITY_REQUIREMENTS = [
    "HelpScout API key في .env",
    "HelpScout Webhook signature مُتحقَّق قبل أي معالجة",
    "Facebook App Secret Proof مع كل طلب Graph API",
    "Facebook Webhook verification token مُتحقَّق",
    "بيانات العميل لا تُشارك بين تذاكر مختلفة",
    "بريد العميل لا يُدرج في Qdrant",
    "resolved_tickets في Qdrant: سؤال وجواب فقط — لا PII",
    "human_verified في Qdrant: يجتاز HUMAN_VERIFIED_KB_QUALIFIER",
    "MULTIPLE_MATCH: لا ربط تلقائي — ملاحظة داخلية فقط",
    "LS: استعلام بيانات ترخيص فقط — لا بيانات دفع",
    "retention: resolved_tickets تُحذف من Qdrant بعد 12 شهراً",
]
```

---

## ٣٠. Error Codes Catalog

```python
SUPPORT_ERROR_CODES = {
    "SUP_WEBHOOK_INVALID":          "Webhook غير صالح أو موقّع خطأ",
    "SUP_TICKET_NOT_FOUND":         "التذكرة غير موجودة في HelpScout",
    "SUP_TEXT_CLEANING_FAILED":     "فشل تنظيف النص الوارد",
    "SUP_CLASSIFIER_JSON_INVALID":  "COMBINED_CLASSIFIER لم يُرجع JSON صالحاً",
    "SUP_UNKNOWN_INTENT":           "النية غير قابلة للتصنيف",
    "SUP_IDENTITY_MULTIPLE_MATCH":  "كيانات متعددة — لا ربط تلقائي",
    "SUP_IDENTITY_RESOLVE_FAILED":  "فشل تحليل هوية العميل",
    "SUP_RAG_EMPTY_RESULTS":        "لا نتائج في قاعدة المعرفة",
    "SUP_QDRANT_UNAVAILABLE":       "Qdrant غير متاح",
    "SUP_KB_NOT_READY":             "قاعدة معرفة القالب لم تُبنَ بعد",
    "SUP_ANSWER_JSON_INVALID":      "ANSWER_GENERATOR لم يُرجع JSON صالحاً",
    "SUP_ANSWER_POLICY_BREACH":     "الإجابة تخرق السياسات",
    "SUP_ANSWER_UNSAFE_TONE":       "نبرة الإجابة غير آمنة",
    "SUP_REPLY_SEND_FAILED":        "فشل إرسال الرد",
    "SUP_ESCALATION_NOTIFY_FAILED": "فشل إرسال بريد التصعيد",
    "SUP_KB_GENERATION_FAILED":     "فشل توليد مقالات المعرفة",
    "SUP_KB_INDEX_FAILED":          "فشل تضمين المقالة في Qdrant",
    "SUP_KB_DEDUP_FAILED":          "فشل فحص التكرار",
    "SUP_FB_FETCH_FAILED":          "فشل جلب تعليقات فيسبوك",
    "SUP_FB_CLASSIFY_FAILED":       "فشل تصنيف التعليق",
    "SUP_FEEDBACK_PARSE_FAILED":    "فشل تحليل الحل البشري",
    "SUP_HUMAN_QUALIFIER_FAILED":   "فشل HUMAN_VERIFIED_KB_QUALIFIER",
}
```

---

## ٣١. بنية الـ State

```python
class SupportState(TypedDict):
    idempotency_key:          str
    incoming_webhook:         Dict
    ticket:                   Optional[SupportTicket]
    detected_language:        str
    identity_resolution:      Optional[IdentityResolution]
    identity_ambiguous:       bool
    customer_verified:        bool
    customer_context:         Dict
    key_issue:                Optional[str]   # في State — ليس في SupportTicket
    discovered_license_key:   Optional[str]
    discovered_order_id:      Optional[str]
    retrieval_plan:           Optional[Dict]
    retrieved_context:        List[Dict]
    retrieval_score:          float
    kb_not_ready:             bool
    generated_answer:         Optional[str]
    answer_confidence:        float
    response_mode:            Optional[ResponseMode]
    answer_citations:         List[AnswerCitation]
    unsupported_claims:       bool
    kb_disclaimer_rendered:   bool   # field منظم — لا عبارات حرفية
    follow_up_needed:         bool
    bug_suspected:            bool
    validation_issues:        List[str]
    route:                    Optional[str]   # من HARD_POLICY_GATE
    route_taken:              Optional[str]   # "reply_direct"|"reply_with_soft_escalation"
    escalation_reason:        Optional[EscalationReason]
    kb_indexing_decision:     Optional[str]   # insert|queue|skip
    status:                   str
    error_code:               Optional[str]
    logs:                     List[str]


class KnowledgeState(TypedDict):
    theme_contract:     Dict
    theme_slug:         str
    version:            str
    articles_generated: List[KnowledgeArticle]
    articles_indexed:   int
    helpscout_doc_ids:  List[str]
    status:             str   # building|ready|failed
    error_code:         Optional[str]
    logs:               List[str]
```

---

## ٣٢. متغيرات البيئة

```env
HELPSCOUT_API_KEY=...
HELPSCOUT_MAILBOX_ID=...
HELPSCOUT_WEBHOOK_SECRET=...
FB_PAGE_ID=...
FB_APP_SECRET=...
FB_PAGE_ACCESS_TOKEN=...
FB_WEBHOOK_VERIFY_TOKEN=...
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=text-embedding-3-small
CLAUDE_API_KEY=sk-ant-...
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com
LS_API_KEY=...
REDIS_URL=redis://localhost:6379
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.60
MIN_QUALIFIER_CONFIDENCE=0.90
MIN_QUALIFIER_RETRIEVAL=0.80
MIN_HUMAN_REPLY_LENGTH=150
MIN_GENERALIZABILITY_SCORE=0.70
MAX_SIMILARITY_THRESHOLD=0.88
RECURRING_ISSUE_THRESHOLD=3
RECURRING_ISSUE_WINDOW_HOURS=48
FB_MONITOR_INTERVAL_MINUTES=15
KB_RETENTION_MONTHS=12
LOG_LEVEL=INFO
```

---

## ٣٣. دستور الوكيل

```markdown
# دستور وكيل الدعم v3

## القواعد المطلقة
١. لا أخترع إجابة — كل ادعاء مستند لـ source_id
٢. لا أرد على تعليقات فيسبوك العامة — أُنبّه بأولوية واضحة
٣. السياسات الصارمة فوق الثقة — billing|legal فوراً
٤. RESOLVED_TICKET_QUALIFIER يحرس resolved_tickets (route_taken="reply_direct")
٥. HUMAN_VERIFIED_KB_QUALIFIER يحرس human_verified (5 شروط)
٦. key_issue في State — ليس في SupportTicket
٧. FacebookCommentIntent مستقل عن TicketIntent
٨. MULTIPLE_MATCH: لا ربط تلقائي — ملاحظة داخلية فقط
٩. SAFE_REPLY_SENDER لا يُرسل للـ QUALIFIER
١٠. check_recurring_issues: key_issue كمعامل صريح مع fallback
١١. kb_disclaimer_rendered: field منظم لا عبارات حرفية
١٢. IDENTITY_RESOLVER: مقارنة على entity_id لا عدد المصادر
١٣. COMBINED_CLASSIFIER: طلب واحد للـ Intent وRisk Flags
```

---

## ٣٤. قائمة التحقق النهائية

### Message Processor

```
□ idempotency_key — لم تُعالَج
□ TEXT_CLEANER: HTML + اقتباسات + توقيعات + تطبيع عربي
□ LANGUAGE_DETECTOR
□ IDENTITY_RESOLVER: مقارنة على entity_id
□ MULTIPLE_MATCH → ملاحظة داخلية — لا ربط تلقائي
□ COMBINED_CLASSIFIER: Intent + RiskFlags طلب واحد
□ HARD_ROUTING_RULES: مُطبَّقة مباشرة بعد التصنيف
□ HARD_POLICY_GATE: billing|legal|refund → escalate_immediate
□ key_issue في State — له fallback في ESCALATION_HANDLER
□ RETRIEVAL_PLANNER: collections + categories بحسب intent
□ RAG_RETRIEVER
□ ANSWER_GENERATOR: JSON مع kb_disclaimer_rendered field
□ ANSWER_VALIDATOR: نبرة + سياسات + citations + kb_disclaimer field
□ CONFIDENCE_ROUTER
□ HIGH   → REPLY_SENDER (route_taken="reply_direct") → QUALIFIER
□ MEDIUM → SAFE_REPLY_SENDER (active) + ملاحظة داخلية
□ LOW    → ESCALATION_HANDLER
□ check_recurring_issues: key_issue كمعامل صريح
□ حدث بالصيغة الموحدة (build_event)
```

### Knowledge Builder

```
□ THEME_BUILD_PRECHECK: idempotency على (theme_slug + version)
□ مقالات: تثبيت + ميزات + WooCommerce + COD + FAQ + presales
□ whats_new (عند THEME_UPDATED_LIVE فقط)
□ DEDUP_CHECKER: similarity < 0.92
□ versioning: supersedes + is_latest
□ Qdrant upsert + HelpScout Docs
□ KB_STATUS_RECORDER: status = "ready"
□ KNOWLEDGE_BASE_UPDATED بالصيغة الموحدة
```

### Facebook Monitor

```
□ كل 15 دقيقة
□ كل تعليق: CommentPriority (6) + FacebookCommentIntent (مستقل)
□ CRITICAL_PUBLIC_RISK → 🔴 إشعار عاجل
□ SALES_OPPORTUNITY    → 🟢 إشعار فرصة
□ SUPPORT_QUESTION     → 🔵 إشعار دعم
□ PRAISE/SPAM          → توثيق فقط
□ لم يُرسَل أي رد آلي
```

### Human Feedback Loop

```
□ HelpScout Webhook: status=closed
□ تحليل الحل البشري + تحديث was_answer_correct
□ إجابة خاطئة → mark_rejected
□ حل قابل للتعميم → HUMAN_VERIFIED_KB_QUALIFIER (5 شروط)
□ insert | queue | skip
```

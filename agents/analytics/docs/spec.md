# وكيل التحليل — عقل مراقبة المنظومة
## وثيقة المواصفات الشاملة v2 — Analytics Agent

> هذه النسخة تجمع v1 + تصحيحات ChatGPT المعتمدة + التصحيحات المعمارية الإضافية.
> تُعدّ المرجع التنفيذي الوحيد المعتمد لوكيل التحليل.

---

## فهرس المحتويات

1. نظرة عامة ومبادئ جوهرية
2. موقع الوكيل في المنظومة الكاملة
3. الطبقات الأربع — معمارية المعالجة
4. Real-time vs Batch — ثنائية المعالجة
5. الكيانات الجوهرية — Domain Model
6. مصادر البيانات — Source of Truth
7. Backfill Policy — سياسة استرجاع البيانات
8. Attribution Model — تقريب المصدر لا Attribution حقيقي
9. Metric Definitions Registry
10. Workflow الأول — Event Collector + Immediate Evaluator
11. Workflow الثاني — Metrics Engine (Batch)
12. Workflow الثالث — Pattern Analyzer (Batch)
13. Workflow الرابع — Signal Generator
14. Workflow الخامس — Report Generator
15. لوحة التحكم — Dashboard Provider
16. Owner Critical Alerts
17. Signal Outcome Feedback Loop
18. Product Registry Dependency
19. Idempotency Strategy
20. Event Contract Schemas
21. أمان وخصوصية البيانات
22. Error Codes Catalog
23. بنية الـ State
24. البيئة المحلية ومتغيرات البيئة
25. دستور الوكيل
26. قائمة التحقق النهائية

---

## ١. نظرة عامة ومبادئ جوهرية

### الهدف

بناء وكيل تحليل يعمل كطبقة استخبارات تشغيلية للمنظومة: يجمع الأحداث، يحوّلها إلى مقاييس محددة الـ granularity، يستخرج نمطين مختلفين (تشغيلي وتجاري)، يُولّد إشارات للوكلاء الستة وتنبيهات مباشرة لصاحب المشروع — بمعالجة Real-time للإشارات العاجلة وBatch للقياس العميق، دون أن يُغيّر أي شيء بنفسه.

### المبادئ غير القابلة للتفاوض

- **`occurred_at` للتحليل — `received_at` للتشخيص** — الوقت الحقيقي للحدث لا وقت استلامه
- **Attribution = تقريب لا حقيقة** — إشارات النشر ليست تفاعلات عميل، الثقة مُعلَنة دائماً
- **Lemon Squeezy مصدر الحقيقة للمبيعات** — Redis مكمّل لا بديل
- **Real-time للإشارات العاجلة فقط** — الأنماط تحتاج بيانات متراكمة
- **Immediate Evaluator مستقل** — الفحوصات التي تحتاج نافذة زمنية تعمل بجانب Event Collector
- **Metric granularity صريح** — كل مقياس له حبّة وقت محددة لا اسم مُضلِّل
- **لا يُغيّر شيئاً** — يقيس ويُبلّغ، التغيير للوكلاء الآخرين
- **الفشل الجزئي لا يوقف الكل** — Pattern Analyzer يكمل رغم فشل detector واحد

---

## ٢. موقع الوكيل في المنظومة الكاملة

### المُدخلات

```
وكيل المنصة  → NEW_SALE, LICENSE_ISSUED, NEW_PRODUCT_LIVE, THEME_UPDATED_LIVE
وكيل الدعم   → SUPPORT_TICKET_RESOLVED, SUPPORT_TICKET_ESCALATED,
               RECURRING_ISSUE_DETECTED, KNOWLEDGE_BASE_UPDATED
وكيل التسويق → POST_PUBLISHED, CAMPAIGN_LAUNCHED
وكيل المحتوى → CONTENT_PRODUCED
وكيل البناء  → THEME_BUILT, THEME_APPROVED
```

### المخرجات

```
صاحب المشروع  ← Dashboard + Reports + Owner Critical Alerts
وكيل التسويق  ← best_time, best_channel, low_sales, campaign_result, best_variant
وكيل المحتوى  ← content_performance, best_content_type
وكيل المنصة   ← pricing_signal, product_signal, license_signal
وكيل البناء   ← build_feedback, recurring_quality_issue
وكيل الدعم    ← support_pattern, support_surge_alert
```

### قاعدة اتجاه العلاقة

وكيل التحليل **لا يأمر** أي وكيل — يُرسل إشارات. كل وكيل مُستلِم يقرر ما يفعل بها بحسب سياسته الخاصة.

---

## ٣. الطبقات الأربع — معمارية المعالجة

```
┌────────────────────────────────────────────────────────────┐
│  طبقة ١ — Event Collection + Immediate Evaluation          │
│  يستقبل الأحداث، يُخزّنها، يُشغّل Immediate Evaluator    │
│  الـ Evaluator منفصل: يتحقق من نوافذ زمنية وbaselines     │
├────────────────────────────────────────────────────────────┤
│  طبقة ٢ — Metrics Engine (Batch — كل ساعة)                 │
│  يحوّل الأحداث إلى مقاييس بـ granularity محدد             │
│  hour → day → week → month (بالتجميع لا إعادة الحساب)     │
├────────────────────────────────────────────────────────────┤
│  طبقة ٣ — Pattern Analyzer (Batch — يومياً)                │
│  نمطان: Operational (تنبيهات) + Business (قرارات)          │
│  الفشل الجزئي لا يوقف الكل                                 │
├────────────────────────────────────────────────────────────┤
│  طبقة ٤ — Signal Generator + Owner Alerts                  │
│  يُرسل إشارات للوكلاء + تنبيهات حرجة لصاحب المشروع       │
│  Signal Outcome يُتتبَّع لتحسين الإشارات لاحقاً            │
└────────────────────────────────────────────────────────────┘
```

---

## ٤. Real-time vs Batch — ثنائية المعالجة

```python
PROCESSING_SCHEDULE = {
    "event_collector":     "مستمر — عند كل حدث وارد",
    "immediate_evaluator": "مستمر — checks تعتمد على نافذة زمنية",
    "metrics_batch":       "كل ساعة — حساب raw hourly metrics",
    "metrics_aggregation": "يومياً — تجميع الساعات إلى أيام",
    "pattern_batch":       "يومياً 03:00 — تحليل الأنماط",
    "reconciliation":      "يومياً — مزامنة مع Lemon Squeezy",
    "weekly_report":       "الأحد 08:00",
    "monthly_report":      "أول الشهر 08:00",
    "retention_cleanup":   "الأحد 02:00",
}

"""
لماذا Real-time للإشارات فقط؟
تشغيل Pattern Analyzer على كل حدث: مكلف وغير مجدٍ.
الأنماط تظهر عبر الزمن لا في لحظة واحدة.

لكن: بعض الإشارات العاجلة تحتاج نافذة زمنية لا تتوفر عند الحدث الواحد.
لذلك Immediate Evaluator يعمل بجانب Event Collector بـ scheduled micro-checks.
"""
```

---

## ٥. الكيانات الجوهرية — Domain Model

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    # Operational — تنبيهات فورية
    NO_OUTPUT_ALERT        = "no_output_alert"       # قالب بلا مبيعات 30 يوم
    SALES_DROP_ALERT       = "sales_drop_alert"      # انخفاض > 50%
    SUPPORT_SURGE_ALERT    = "support_surge_alert"   # 10+ تذاكر / 24 ساعة
    CAMPAIGN_NO_OUTPUT     = "campaign_no_output"    # حملة بلا نشر 24 ساعة
    RECURRING_QUALITY_ISSUE = "recurring_quality_issue"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"

    # Business — للوكلاء
    BEST_TIME              = "best_time"
    BEST_CHANNEL           = "best_channel"
    LOW_SALES              = "low_sales"
    HIGH_INTEREST          = "high_interest"
    CAMPAIGN_RESULT        = "campaign_result"
    BEST_VARIANT           = "best_variant"
    CONTENT_PERFORMANCE    = "content_performance"
    BEST_CONTENT_TYPE      = "best_content_type"
    PRICING_SIGNAL         = "pricing_signal"
    PRODUCT_SIGNAL         = "product_signal"
    LICENSE_SIGNAL         = "license_signal"
    BUILD_FEEDBACK         = "build_feedback"
    SUPPORT_PATTERN        = "support_pattern"


class SignalPriority(Enum):
    IMMEDIATE = "immediate"
    DAILY     = "daily"
    WEEKLY    = "weekly"


class AttributionConfidence(Enum):
    HIGH   = "high"    # UTM parameters أو referral token صريح
    MEDIUM = "medium"  # نشر مؤكد + بيع في نافذة 24 ساعة
    LOW    = "low"     # استنتاج من تسلسل النشر فقط — الأكثر شيوعاً في v1


class AttributionChannel(Enum):
    FACEBOOK  = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK    = "tiktok"
    EMAIL     = "email"
    WHATSAPP  = "whatsapp"
    DIRECT    = "direct"
    ORGANIC   = "organic"
    UNKNOWN   = "unknown"


class AnalyticsType(Enum):
    OPERATIONAL = "operational"  # support surge, quality issues, publish failures
    BUSINESS    = "business"     # sales trend, best channel, stagnant product


@dataclass
class AnalyticsEvent:
    """حدث خام — طبقة Collection"""
    event_id:     str
    event_type:   str
    source_agent: str
    theme_slug:   Optional[str]
    raw_data:     Dict[str, Any]
    occurred_at:  datetime    # وقت وقوع الحدث الحقيقي — للتحليل
    received_at:  datetime    # وقت الاستلام من Redis — للتشخيص
    processed:    bool = False


@dataclass
class MetricSnapshot:
    """مقياس مُحسَّب — طبقة Metrics"""
    metric_id:    str
    metric_key:   str           # من METRIC_DEFINITIONS
    theme_slug:   Optional[str]
    channel:      Optional[str]
    granularity:  str           # "hour" | "day" | "week" | "month"
    period_start: datetime
    period_end:   datetime
    value:        float
    unit:         str
    computed_at:  datetime


@dataclass
class Pattern:
    """نمط مكتشف — طبقة Pattern Analyzer"""
    pattern_id:         str
    pattern_type:       str
    analytics_type:     AnalyticsType
    theme_slug:         Optional[str]
    channel:            Optional[str]
    description:        str
    confidence:         float
    supporting_metrics: List[str]
    detected_at:        datetime
    is_actionable:      bool


@dataclass
class AnalyticsSignal:
    """إشارة مُولَّدة — طبقة Signal Generator"""
    signal_id:             str
    signal_type:           SignalType
    priority:              SignalPriority
    target_agent:          str
    theme_slug:            Optional[str]
    channel:               Optional[str]
    recommendation:        str
    confidence:            float
    supporting_pattern_id: Optional[str]
    data:                  Dict[str, Any]
    generated_at:          datetime
    sent_at:               Optional[datetime]


@dataclass
class AttributionRecord:
    """ربط البيع بمصدره التقريبي"""
    sale_id:            str
    theme_slug:         str
    amount_usd:         float
    license_tier:       str
    channels_touched:   List[AttributionChannel]
    attributed_to:      AttributionChannel
    attribution_model:  str               # "last_touch_v1"
    attribution_confidence: AttributionConfidence  # دائماً مُعلَن
    attribution_note:   str               # توضيح ما تم استنتاجه
    sale_date:          datetime          # من occurred_at


@dataclass
class SignalOutcome:
    """نتيجة إشارة — لتحسين الإشارات مستقبلاً"""
    outcome_id:          str
    signal_id:           str
    target_agent:        str
    action_taken:        Optional[str]
    observed_metric:     Optional[str]   # المقياس الذي يُقيّم النتيجة
    before_value:        Optional[float]
    after_value:         Optional[float]
    outcome_window_days: int
    success_score:       Optional[float]  # 0.0 - 1.0
    evaluated_at:        Optional[datetime]
    notes:               Optional[str]


@dataclass
class WeeklyReport:
    report_id:        str
    period_start:     datetime
    period_end:       datetime
    total_sales:      int
    total_revenue:    float
    top_theme:        Optional[str]
    top_channel:      Optional[str]
    support_tickets:  int
    escalation_rate:  float          # escalated_count / resolved_count
    new_products:     int
    signals_sent:     int
    highlights:       List[str]
    concerns:         List[str]
    generated_at:     datetime
```

---

## ٦. مصادر البيانات — Source of Truth

```python
SOURCE_OF_TRUTH = {
    "sales":     {"primary": "lemon_squeezy_api", "secondary": "redis_events",
                  "conflict_resolution": "primary_wins"},
    "licenses":  {"primary": "lemon_squeezy_api", "secondary": "redis_events",
                  "conflict_resolution": "primary_wins"},
    "support":   {"primary": "helpscout_api",      "secondary": "redis_events",
                  "conflict_resolution": "primary_wins"},
    "marketing": {"primary": "redis_events",       "secondary": None,
                  "conflict_resolution": "no_primary"},
    "content":   {"primary": "redis_events",       "secondary": None,
                  "conflict_resolution": "no_primary"},
    "builds":    {"primary": "redis_events",       "secondary": None,
                  "conflict_resolution": "no_primary"},
}


def reconcile_sales_data() -> None:
    """
    يُشغَّل يومياً — يُقارن Redis مع Lemon Squeezy.
    يُصحّح التباين ويُطلق RECONCILIATION_MISMATCH إن كبر الفرق.
    """
    ls_orders    = ls_client.get_orders(since=yesterday(), use_occurred_at=True)
    redis_events = event_store.get_events("NEW_SALE", since=yesterday())

    ls_ids    = {o["id"] for o in ls_orders}
    redis_ids = {e["data"].get("order_id") for e in redis_events}

    missing_in_redis = ls_ids - redis_ids
    extra_in_redis   = redis_ids - ls_ids

    for order_id in missing_in_redis:
        order = ls_client.get_order(order_id)
        event_store.backfill_sale(order)

    if len(missing_in_redis) > 5 or len(extra_in_redis) > 5:
        emit_immediate_signal(
            signal_type = SignalType.RECONCILIATION_MISMATCH,
            theme_slug  = None,
            data        = {
                "missing_in_redis": len(missing_in_redis),
                "extra_in_redis":   len(extra_in_redis),
            },
            target_agent = "owner",
        )
```

---

## ٧. Backfill Policy — سياسة استرجاع البيانات

```python
BACKFILL_POLICY = {
    "sales": {
        "reconstructable": True,
        "source":          "lemon_squeezy_api",
        "method":          "GET /orders?created_after=X",
        "note":            "يمكن استرجاع كل المبيعات من LS مهما تأخر الحدث",
    },
    "licenses": {
        "reconstructable": True,
        "source":          "lemon_squeezy_api",
        "method":          "GET /licenses?created_after=X",
    },
    "support": {
        "reconstructable": True,
        "source":          "helpscout_api",
        "method":          "GET /conversations?since=X",
    },
    "marketing": {
        "reconstructable": False,
        "policy":          "best_effort_only",
        "note":            "أحداث النشر لا يمكن استرجاعها إن ضاعت من Redis",
    },
    "content": {
        "reconstructable": False,
        "policy":          "best_effort_only",
    },
    "builds": {
        "reconstructable": False,
        "policy":          "best_effort_only",
    },
}

"""
التبعة العملية:
  - إن تعطّل وكيل التحليل ساعة:
    → مبيعات + دعم: قابلة للاسترجاع الكامل
    → تسويق + محتوى: ستكون هناك فجوات في التحليل — مقبولة في v1
"""
```

---

## ٨. Attribution Model — تقريب المصدر لا Attribution حقيقي

```python
"""
Attribution في v1 = Marketing Influence Approximation

لماذا؟
POST_PUBLISHED و CAMPAIGN_LAUNCHED هي أحداث نشر — لا أحداث استهلاك عميل.
لا يوجد تتبع جلسة أو UTM parameters أو click events.
نستنتج من تسلسل الأحداث — والثقة مُعلَنة دائماً.

Attribution Confidence:
HIGH   = UTM parameter موجود في رابط المنشور (نادر في v1)
MEDIUM = نشر مؤكد + بيع في نافذة 24 ساعة من نفس القناة
LOW    = استنتاج من تسلسل النشر في نافذة 7 أيام — الأكثر شيوعاً
"""

ATTRIBUTION_MODEL = "last_touch_v1"
ATTRIBUTION_WINDOW_DAYS = 7


def attribute_sale(
    sale_id:    str,
    sale_date:  datetime,   # من occurred_at — ليس received_at
    theme_slug: str,
    amount_usd: float,
    license_tier: str,
) -> AttributionRecord:

    window_start = sale_date - timedelta(days=ATTRIBUTION_WINDOW_DAYS)

    recent_posts = event_store.get_events(
        event_types = ["POST_PUBLISHED", "CAMPAIGN_LAUNCHED"],
        theme_slug  = theme_slug,
        since       = window_start,
        before      = sale_date,
        order_by    = "occurred_at",  # الوقت الحقيقي
    )

    recent_emails = event_store.get_events(
        event_types = ["CONTENT_READY"],
        theme_slug  = theme_slug,
        since       = window_start,
        before      = sale_date,
    )

    channels_touched = []
    for post in sorted(recent_posts, key=lambda x: x["occurred_at"]):
        channel = AttributionChannel(post["data"].get("channel", "unknown"))
        if channel not in channels_touched:
            channels_touched.append(channel)

    if recent_emails:
        channels_touched.append(AttributionChannel.EMAIL)

    # تحديد الثقة
    time_since_last_post = None
    if recent_posts:
        last_post_time = max(p["occurred_at"] for p in recent_posts)
        time_since_last_post = (sale_date - last_post_time).total_seconds() / 3600

    if time_since_last_post is not None and time_since_last_post <= 24:
        confidence = AttributionConfidence.MEDIUM
    elif channels_touched:
        confidence = AttributionConfidence.LOW
    else:
        confidence = AttributionConfidence.LOW

    attributed_to = (
        channels_touched[-1] if channels_touched
        else AttributionChannel.DIRECT
    )

    return AttributionRecord(
        sale_id               = sale_id,
        theme_slug            = theme_slug,
        amount_usd            = amount_usd,
        license_tier          = license_tier,
        channels_touched      = channels_touched,
        attributed_to         = attributed_to,
        attribution_model     = ATTRIBUTION_MODEL,
        attribution_confidence = confidence,
        attribution_note      = (
            f"استنتاج من {len(recent_posts)} منشور في نافذة {ATTRIBUTION_WINDOW_DAYS} أيام. "
            f"ثقة: {confidence.value}. "
            "هذا تقريب لا Attribution دقيق."
        ),
        sale_date = sale_date,
    )
```

---

## ٩. Metric Definitions Registry

```python
"""
كل مقياس له تعريف رسمي: المصدر، الصيغة، الـ granularity، الوحدة.
يمنع التضارب والتسمية المُضلِّلة.
"""

METRIC_DEFINITIONS = {

    "sales_count": {
        "source":       "lemon_squeezy_api",
        "formula":      "count(orders WHERE status='paid')",
        "granularity":  ["hour", "day", "week", "month"],
        "unit":         "count",
        "event_type":   "NEW_SALE",
        "time_field":   "occurred_at",
    },

    "sales_revenue": {
        "source":       "lemon_squeezy_api",
        "formula":      "sum(orders.total_usd WHERE status='paid')",
        "granularity":  ["hour", "day", "week", "month"],
        "unit":         "usd",
        "event_type":   "NEW_SALE",
        "time_field":   "occurred_at",
    },

    "sales_by_theme": {
        "source":       "lemon_squeezy_api",
        "formula":      "count(orders) GROUP BY theme_slug",
        "granularity":  ["day", "week", "month"],
        "unit":         "count",
        "dimensions":   ["theme_slug"],
    },

    "sales_by_channel": {
        "source":       "attribution_records",
        "formula":      "count(attribution_records) GROUP BY attributed_to",
        "granularity":  ["day", "week", "month"],
        "unit":         "count",
        "dimensions":   ["attributed_to"],
        "note":         "مبني على Attribution Approximation — LOW confidence الغالب",
    },

    "support_ticket_resolved": {
        "source":       "helpscout_api",
        "formula":      "count(conversations WHERE status='closed')",
        "granularity":  ["hour", "day", "week"],
        "unit":         "count",
        "event_type":   "SUPPORT_TICKET_RESOLVED",
        "time_field":   "occurred_at",
    },

    "support_ticket_escalated": {
        "source":       "helpscout_api",
        "formula":      "count(conversations WHERE escalated=True)",
        "granularity":  ["hour", "day", "week"],
        "unit":         "count",
        "event_type":   "SUPPORT_TICKET_ESCALATED",
        "time_field":   "occurred_at",
    },

    "support_escalation_rate": {
        "source":       "derived",
        "formula":      "support_ticket_escalated / support_ticket_resolved",
        "granularity":  ["day", "week"],
        "unit":         "ratio",
        "note":         "لا تُجمَّع rates — تُحسَّب من الـ counts",
    },

    "support_avg_resolution_minutes": {
        "source":       "helpscout_api",
        "formula":      "avg(conversation.resolved_at - conversation.created_at)",
        "granularity":  ["day", "week"],
        "unit":         "minutes",
    },

    "posts_published": {
        "source":       "redis_events",
        "formula":      "count(POST_PUBLISHED events)",
        "granularity":  ["hour", "day", "week"],
        "unit":         "count",
        "event_type":   "POST_PUBLISHED",
        "time_field":   "occurred_at",
    },

    "posts_by_channel": {
        "source":       "redis_events",
        "formula":      "count(POST_PUBLISHED) GROUP BY channel",
        "granularity":  ["day", "week"],
        "unit":         "count",
        "dimensions":   ["channel"],
    },

    "campaign_conversion_rate": {
        "source":       "derived",
        "formula":      "sales_by_channel / posts_by_channel",
        "granularity":  ["week", "month"],
        "unit":         "ratio",
        "note":         "تقريبي — Attribution LOW confidence",
    },

    "content_produced": {
        "source":       "redis_events",
        "formula":      "count(CONTENT_PRODUCED events)",
        "granularity":  ["day", "week"],
        "unit":         "count",
        "event_type":   "CONTENT_PRODUCED",
    },

    "license_tier_distribution": {
        "source":       "lemon_squeezy_api",
        "formula":      "count(licenses) GROUP BY tier",
        "granularity":  ["day", "week", "month"],
        "unit":         "count",
        "dimensions":   ["license_tier"],
    },
}


def get_metric_definition(metric_key: str) -> dict:
    if metric_key not in METRIC_DEFINITIONS:
        raise ConfigurationError(f"ANL_METRIC_NOT_DEFINED: {metric_key}")
    return METRIC_DEFINITIONS[metric_key]
```

---

## ١٠. Workflow الأول — Event Collector + Immediate Evaluator

### الفصل بين الاثنين

```python
"""
Event Collector: يستقبل ويُخزّن — سريع جداً
Immediate Evaluator: يتحقق من نوافذ زمنية — يعمل بجانبه

بعض الإشارات "الفورية" تحتاج نافذة زمنية:
  - sales_drop_50pct: تحتاج baseline الأسبوع الماضي
  - campaign_no_output_24h: تحتاج مرور 24 ساعة
  - no_sales_30_days: تحتاج جدولة مؤجلة 30 يوماً

هذه لا يمكن فحصها على حدث واحد.
لذلك Immediate Evaluator يعمل كـ micro-scheduler.
"""
```

### Event Collector

```python
def event_collector_node(event: dict) -> None:
    """
    سريع جداً — تخزين فقط + trigger للـ Evaluator.
    """
    # استخراج occurred_at من الحدث (الوقت الحقيقي)
    occurred_at = parse_datetime(event.get("occurred_at")) or datetime.utcnow()
    received_at = datetime.utcnow()

    analytics_event = AnalyticsEvent(
        event_id     = event["event_id"],
        event_type   = event["event_type"],
        source_agent = event["source"],
        theme_slug   = event["data"].get("theme_slug"),
        raw_data     = event["data"],
        occurred_at  = occurred_at,    # للتحليل
        received_at  = received_at,    # للتشخيص
        processed    = False,
    )

    # فحص idempotency
    if event_store.exists(analytics_event.event_id):
        return

    event_store.save(analytics_event)

    # Attribution فوري عند البيع
    if event["event_type"] == "NEW_SALE":
        attribution_record = attribute_sale(
            sale_id      = event["data"]["order_id"],
            sale_date    = occurred_at,  # occurred_at — ليس received_at
            theme_slug   = event["data"].get("theme_slug", "unknown"),
            amount_usd   = event["data"].get("amount_usd", 0),
            license_tier = event["data"].get("license_tier", "unknown"),
        )
        attribution_store.save(attribution_record)

    # تفويض للـ Immediate Evaluator
    immediate_evaluator.on_new_event(analytics_event)
```

### Immediate Evaluator

```python
class ImmediateEvaluator:
    """
    يعمل بجانب Event Collector — يتحقق من حالات تحتاج نافذة زمنية.
    """

    def on_new_event(self, event: AnalyticsEvent) -> None:
        """يُشغَّل على كل حدث جديد — checks خفيفة فقط."""

        # فحص: ارتفاع تذاكر الدعم
        if event.event_type == "SUPPORT_TICKET_ESCALATED":
            self._check_support_surge(event.theme_slug)

        # فحص: مشكلة جودة متكررة
        if event.event_type == "RECURRING_ISSUE_DETECTED":
            emit_immediate_signal(
                signal_type  = SignalType.RECURRING_QUALITY_ISSUE,
                theme_slug   = event.theme_slug,
                data         = event.raw_data,
                target_agent = "builder_agent",
            )

        # جدولة فحوصات مؤجلة
        if event.event_type == "NEW_PRODUCT_LIVE":
            self._schedule_no_sales_check(event.theme_slug, after_days=30)

        if event.event_type == "CAMPAIGN_LAUNCHED":
            self._schedule_campaign_output_check(
                event.raw_data.get("campaign_id"),
                after_hours=24,
            )


    def _check_support_surge(self, theme_slug: Optional[str]) -> None:
        """يفحص النافذة الزمنية لتذاكر الدعم."""
        count = event_store.count_events(
            event_type = "SUPPORT_TICKET_ESCALATED",
            theme_slug = theme_slug,
            since      = datetime.utcnow() - timedelta(hours=24),
        )
        if count >= IMMEDIATE_THRESHOLDS["support_surge"]["threshold"]:
            emit_immediate_signal(
                signal_type  = SignalType.SUPPORT_SURGE_ALERT,
                theme_slug   = theme_slug,
                data         = {"ticket_count": count, "window_hours": 24},
                target_agent = "support_agent",
            )


    def run_scheduled_checks(self) -> None:
        """
        يُشغَّل كل 15 دقيقة — للفحوصات المؤجلة.
        """
        self._check_no_sales_products()
        self._check_campaign_outputs()
        self._check_sales_drop()


    def _check_no_sales_products(self) -> None:
        """يفحص القوالب التي لم تُباع منذ 30 يوماً."""
        threshold_date = datetime.utcnow() - timedelta(days=30)

        for theme_slug in product_registry.get_all_published_slugs():
            last_sale = event_store.get_last_event(
                event_type = "NEW_SALE",
                theme_slug = theme_slug,
            )
            launch_date = product_registry.get_launch_date(theme_slug)

            reference_date = last_sale["occurred_at"] if last_sale else launch_date

            if reference_date and reference_date < threshold_date:
                # تحقق: هل أُرسلت الإشارة مؤخراً؟ (لا تكرار كل 15 دقيقة)
                if not signal_store.sent_recently(
                    SignalType.NO_OUTPUT_ALERT, theme_slug, hours=24
                ):
                    emit_immediate_signal(
                        signal_type  = SignalType.NO_OUTPUT_ALERT,
                        theme_slug   = theme_slug,
                        data         = {"days_since_sale": (datetime.utcnow() - reference_date).days},
                        target_agent = "marketing_agent",
                    )


    def _check_sales_drop(self) -> None:
        """يفحص انخفاض المبيعات مقارنة بالأسبوع الماضي."""
        this_week = metric_store.sum("sales_count", days=7, granularity="day")
        last_week = metric_store.sum("sales_count", days=7, offset_days=7, granularity="day")

        if last_week > 0:
            drop_rate = (last_week - this_week) / last_week
            if drop_rate >= 0.50:
                if not signal_store.sent_recently(
                    SignalType.SALES_DROP_ALERT, None, hours=48
                ):
                    emit_immediate_signal(
                        signal_type  = SignalType.SALES_DROP_ALERT,
                        theme_slug   = None,
                        data         = {"drop_rate": drop_rate, "this_week": this_week, "last_week": last_week},
                        target_agent = "marketing_agent",
                    )


    def _check_campaign_outputs(self) -> None:
        """يفحص الحملات التي لم تُنتج منشوراً بعد 24 ساعة."""
        cutoff = datetime.utcnow() - timedelta(hours=24)

        active_campaigns = event_store.get_events(
            event_type = "CAMPAIGN_LAUNCHED",
            before     = cutoff,
        )

        for campaign_event in active_campaigns:
            campaign_id = campaign_event["data"].get("campaign_id")
            posts = event_store.count_events(
                event_type  = "POST_PUBLISHED",
                filter_data = {"campaign_id": campaign_id},
                since       = parse_datetime(campaign_event["occurred_at"]),
            )

            if posts == 0 and not signal_store.sent_recently(
                SignalType.CAMPAIGN_NO_OUTPUT, None, hours=24,
                filter_key=campaign_id,
            ):
                emit_immediate_signal(
                    signal_type  = SignalType.CAMPAIGN_NO_OUTPUT,
                    theme_slug   = campaign_event["data"].get("theme_slug"),
                    data         = {"campaign_id": campaign_id, "hours_elapsed": 24},
                    target_agent = "marketing_agent",
                )


IMMEDIATE_THRESHOLDS = {
    "no_sales_days":    {"threshold": 30, "signal": SignalType.NO_OUTPUT_ALERT},
    "sales_drop_rate":  {"threshold": 0.50, "signal": SignalType.SALES_DROP_ALERT},
    "support_surge":    {"threshold": 10, "signal": SignalType.SUPPORT_SURGE_ALERT},
    "campaign_no_output_hours": {"threshold": 24, "signal": SignalType.CAMPAIGN_NO_OUTPUT},
    "recurring_quality": {"threshold": 3, "signal": SignalType.RECURRING_QUALITY_ISSUE},
}
```

---

## ١١. Workflow الثاني — Metrics Engine (Batch)

```python
"""
يُشغَّل كل ساعة — يحسب Hourly metrics.
Aggregation يومي يبني Daily من Hourly بالتجميع.
لا إعادة حساب — تجميع فقط.
"""

def metrics_engine_batch() -> None:
    now          = datetime.utcnow()
    period_start = now - timedelta(hours=1)

    for metric_key, definition in METRIC_DEFINITIONS.items():
        if "hour" not in definition["granularity"]:
            continue  # لا تُحسَّب في الـ hourly batch

        try:
            value = compute_metric_for_period(
                metric_key   = metric_key,
                definition   = definition,
                period_start = period_start,
                period_end   = now,
                granularity  = "hour",
            )

            snapshot = MetricSnapshot(
                metric_id    = str(uuid.uuid4()),
                metric_key   = metric_key,
                theme_slug   = None,
                channel      = None,
                granularity  = "hour",
                period_start = period_start,
                period_end   = now,
                value        = value,
                unit         = definition["unit"],
                computed_at  = now,
            )
            metric_store.save(snapshot)

        except Exception as e:
            # الفشل الجزئي لا يوقف العملية
            log.error(f"ANL_METRIC_COMPUTE_FAILED: {metric_key}: {e}")
            continue


def daily_aggregation() -> None:
    """
    يُشغَّل يومياً — يُجمّع الساعات إلى أيام.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    today_end   = today_start + timedelta(days=1)

    for metric_key, definition in METRIC_DEFINITIONS.items():
        if "day" not in definition["granularity"]:
            continue

        hourly_snapshots = metric_store.get_range(
            metric_key   = metric_key,
            granularity  = "hour",
            since        = today_start,
            before       = today_end,
        )

        if not hourly_snapshots:
            continue

        # تجميع بحسب نوع المقياس
        unit = definition["unit"]
        if unit in ("count", "usd"):
            daily_value = sum(s.value for s in hourly_snapshots)
        elif unit == "ratio":
            # الـ ratio يُحسَّب من الـ counts لا يُجمَّع
            daily_value = compute_ratio_for_day(metric_key, today_start, today_end)
        else:
            daily_value = sum(s.value for s in hourly_snapshots) / len(hourly_snapshots)

        metric_store.save(MetricSnapshot(
            metric_id    = str(uuid.uuid4()),
            metric_key   = metric_key,
            granularity  = "day",
            period_start = today_start,
            period_end   = today_end,
            value        = daily_value,
            unit         = unit,
            computed_at  = datetime.utcnow(),
        ))
```

---

## ١٢. Workflow الثالث — Pattern Analyzer (Batch)

```python
"""
يُشغَّل يومياً 03:00.
نمطان: Operational (تنبيهات) + Business (قرارات).
الفشل الجزئي لا يوقف الكل.
"""

OPERATIONAL_DETECTORS = [
    detect_support_surge_pattern,
    detect_quality_patterns,
    detect_stagnant_products,
]

BUSINESS_DETECTORS = [
    detect_declining_sales,
    detect_channel_performance,
    detect_content_performance,
    detect_license_trends,
]


def pattern_analyzer_batch() -> None:
    all_patterns = []
    failed_detectors = []

    for detector in OPERATIONAL_DETECTORS + BUSINESS_DETECTORS:
        try:
            detected = detector()
            all_patterns.extend(detected)
        except Exception as e:
            failed_detectors.append(detector.__name__)
            log.error(f"ANL_PATTERN_DETECT_FAILED: {detector.__name__}: {e}")
            # يكمل — لا يتوقف

    # تسجيل الأنماط
    for pattern in all_patterns:
        pattern_store.save(pattern)
        if pattern.is_actionable:
            signal_generator(pattern)

    # تقرير الفشل الجزئي
    if failed_detectors:
        log.warning(f"Pattern Analyzer أكمل مع فشل جزئي: {failed_detectors}")


def detect_stagnant_products() -> List[Pattern]:
    """
    يفحص القوالب الراكدة — من product_registry (read-only).
    Batching لمنع N+1 queries.
    """
    patterns      = []
    threshold_date = datetime.utcnow() - timedelta(days=30)

    # جلب كل القوالب في استعلام واحد
    all_themes       = product_registry.get_all_published()
    all_last_sales   = event_store.get_last_sales_bulk(
        theme_slugs = [t["theme_slug"] for t in all_themes]
    )

    for theme in all_themes:
        slug       = theme["theme_slug"]
        last_sale  = all_last_sales.get(slug)
        launch_date = parse_datetime(theme.get("published_at"))

        reference = last_sale["occurred_at"] if last_sale else launch_date

        if reference and reference < threshold_date:
            days = (datetime.utcnow() - reference).days
            patterns.append(Pattern(
                pattern_id          = str(uuid.uuid4()),
                pattern_type        = "product_stagnation",
                analytics_type      = AnalyticsType.BUSINESS,
                theme_slug          = slug,
                channel             = None,
                description         = f"{theme['theme_name_ar']} لم يُباع منذ {days} يوم",
                confidence          = 1.0,
                supporting_metrics  = ["sales_by_theme"],
                detected_at         = datetime.utcnow(),
                is_actionable       = True,
            ))

    return patterns


def detect_declining_sales() -> List[Pattern]:
    patterns  = []
    this_week = metric_store.sum("sales_count", days=7, granularity="day")
    last_week = metric_store.sum("sales_count", days=7, offset_days=7, granularity="day")

    if last_week > 0:
        change = (this_week - last_week) / last_week
        if change < -0.30:
            patterns.append(Pattern(
                pattern_id        = str(uuid.uuid4()),
                pattern_type      = "declining_sales",
                analytics_type    = AnalyticsType.BUSINESS,
                theme_slug        = None,
                channel           = None,
                description       = f"انخفاض مبيعات {abs(change):.0%} مقارنة بالأسبوع الماضي",
                confidence        = 0.85,
                supporting_metrics = ["sales_count"],
                detected_at       = datetime.utcnow(),
                is_actionable     = True,
            ))

    return patterns


def detect_channel_performance() -> List[Pattern]:
    patterns         = []
    sales_by_channel = attribution_store.get_sales_by_channel(days=30)
    posts_by_channel = metric_store.get_per_channel("posts_by_channel", days=30)

    for channel, posts in posts_by_channel.items():
        if posts < 5:  # بيانات غير كافية
            continue

        sales     = sales_by_channel.get(channel, 0)
        conv_rate = sales / posts

        analytics_type = AnalyticsType.BUSINESS

        if conv_rate > 0.10:
            patterns.append(Pattern(
                pattern_id        = str(uuid.uuid4()),
                pattern_type      = "high_performing_channel",
                analytics_type    = analytics_type,
                theme_slug        = None,
                channel           = channel,
                description       = f"قناة {channel}: معدل تحويل {conv_rate:.1%} (تقريبي — LOW confidence)",
                confidence        = 0.70,   # مخفَّض لأن Attribution تقريبي
                supporting_metrics = ["posts_by_channel", "sales_by_channel"],
                detected_at       = datetime.utcnow(),
                is_actionable     = True,
            ))
        elif conv_rate < 0.01:
            patterns.append(Pattern(
                pattern_id        = str(uuid.uuid4()),
                pattern_type      = "low_performing_channel",
                analytics_type    = analytics_type,
                theme_slug        = None,
                channel           = channel,
                description       = f"قناة {channel}: معدل تحويل منخفض {conv_rate:.1%} من {posts} منشور (تقريبي)",
                confidence        = 0.65,
                supporting_metrics = ["posts_by_channel", "sales_by_channel"],
                detected_at       = datetime.utcnow(),
                is_actionable     = True,
            ))

    return patterns
```

---

## ١٣. Workflow الرابع — Signal Generator

```python
SIGNAL_ROUTING = {
    SignalType.NO_OUTPUT_ALERT:         "marketing_agent",
    SignalType.SALES_DROP_ALERT:        "marketing_agent",
    SignalType.SUPPORT_SURGE_ALERT:     "support_agent",
    SignalType.CAMPAIGN_NO_OUTPUT:      "marketing_agent",
    SignalType.RECURRING_QUALITY_ISSUE: "builder_agent",
    SignalType.RECONCILIATION_MISMATCH: "owner",

    SignalType.BEST_TIME:               "marketing_agent",
    SignalType.BEST_CHANNEL:            "marketing_agent",
    SignalType.LOW_SALES:               "marketing_agent",
    SignalType.HIGH_INTEREST:           "marketing_agent",
    SignalType.CAMPAIGN_RESULT:         "marketing_agent",
    SignalType.BEST_VARIANT:            "marketing_agent",

    SignalType.CONTENT_PERFORMANCE:     "content_agent",
    SignalType.BEST_CONTENT_TYPE:       "content_agent",

    SignalType.PRICING_SIGNAL:          "platform_agent",
    SignalType.PRODUCT_SIGNAL:          "platform_agent",
    SignalType.LICENSE_SIGNAL:          "platform_agent",

    SignalType.BUILD_FEEDBACK:          "builder_agent",
    SignalType.SUPPORT_PATTERN:         "support_agent",
}


def emit_immediate_signal(
    signal_type:  SignalType,
    theme_slug:   Optional[str],
    data:         dict,
    target_agent: Optional[str] = None,
) -> None:
    target = target_agent or SIGNAL_ROUTING.get(signal_type)
    if not target:
        return

    signal = AnalyticsSignal(
        signal_id             = str(uuid.uuid4()),
        signal_type           = signal_type,
        priority              = SignalPriority.IMMEDIATE,
        target_agent          = target,
        theme_slug            = theme_slug,
        channel               = None,
        recommendation        = build_recommendation(signal_type, data),
        confidence            = 1.0,  # إشارات فورية مبنية على حقائق
        supporting_pattern_id = None,
        data                  = data,
        generated_at          = datetime.utcnow(),
        sent_at               = None,
    )

    signal_store.save(signal)
    dispatch_signal(signal)

    # Owner Critical Alerts
    if signal_type in OWNER_CRITICAL_SIGNALS:
        send_owner_critical_alert(signal)

    # تسجيل Signal Outcome stub للمتابعة
    signal_outcome_tracker.register(signal)


def dispatch_signal(signal: AnalyticsSignal) -> None:
    channel_map = {
        "marketing_agent": "marketing_events",
        "builder_agent":   "builder_events",
        "support_agent":   "support_events",
        "platform_agent":  "platform_events",
        "content_agent":   "content_events",
        "owner":           None,   # يصل عبر Resend مباشرة
    }

    redis_channel = channel_map.get(signal.target_agent)
    if redis_channel:
        event = build_event(
            event_type     = "ANALYTICS_SIGNAL",
            source         = "analytics_agent",
            correlation_id = f"signal:{signal.signal_id}",
            data           = {
                "signal_id":      signal.signal_id,
                "signal_type":    signal.signal_type.value,
                "theme_slug":     signal.theme_slug,
                "channel":        signal.channel,
                "recommendation": signal.recommendation,
                "confidence":     signal.confidence,
                "data":           signal.data,
            },
        )
        redis.publish(redis_channel, json.dumps(event))

    signal.sent_at = datetime.utcnow()
    signal_store.update_sent_at(signal.signal_id, signal.sent_at)
```

---

## ١٤. Workflow الخامس — Report Generator

```python
def generate_weekly_report() -> WeeklyReport:
    now          = datetime.utcnow()
    period_start = now - timedelta(days=7)

    total_sales   = metric_store.sum("sales_count",   period_start, now, granularity="day")
    total_revenue = metric_store.sum("sales_revenue",  period_start, now, granularity="day")
    top_theme     = metric_store.top_by_theme("sales_by_theme", period_start, now)
    top_channel   = attribution_store.top_channel(period_start, now)

    # حساب escalation_rate من counts لا من rates
    resolved_count  = metric_store.sum("support_ticket_resolved",  period_start, now, granularity="day")
    escalated_count = metric_store.sum("support_ticket_escalated", period_start, now, granularity="day")
    esc_rate        = escalated_count / resolved_count if resolved_count > 0 else 0

    new_products  = event_store.count_events("NEW_PRODUCT_LIVE", period_start, now)
    signals_sent  = signal_store.count(period_start, now)

    patterns    = pattern_store.get_actionable(period_start, now)
    highlights  = [p.description for p in patterns if "high_performing" in p.pattern_type]
    concerns    = [p.description for p in patterns if p.pattern_type in (
        "declining_sales", "product_stagnation", "support_surge_pattern"
    )]

    report = WeeklyReport(
        report_id       = str(uuid.uuid4()),
        period_start    = period_start,
        period_end      = now,
        total_sales     = int(total_sales),
        total_revenue   = total_revenue,
        top_theme       = top_theme,
        top_channel     = top_channel,
        support_tickets = int(resolved_count + escalated_count),
        escalation_rate = esc_rate,   # من counts — صحيح
        new_products    = int(new_products),
        signals_sent    = signals_sent,
        highlights      = highlights[:5],
        concerns        = concerns[:5],
        generated_at    = now,
    )

    report_store.save(report)
    send_report_to_owner(report)
    return report
```

---

## ١٥. لوحة التحكم — Dashboard Provider

```python
def get_dashboard_data(period: str = "30d", theme_slug: Optional[str] = None) -> dict:
    """
    لصاحب المشروع فقط — on-demand، لا ترسل أحداثاً.
    كل الأوقات مبنية على occurred_at.
    Attribution confidence مُعلَن في كل metric مرتبط به.
    """
    period_start = datetime.utcnow() - parse_period(period)

    return {
        "sales": {
            "total":        metric_store.sum("sales_count",    period_start, granularity="day"),
            "revenue":      metric_store.sum("sales_revenue",  period_start, granularity="day"),
            "by_theme":     metric_store.get_per_theme("sales_by_theme",   period_start),
            "by_channel":   attribution_store.get_sales_by_channel(period_start),
            "attribution_note": "القناة مُستنتجة بثقة LOW في معظم الحالات — راجع Attribution Model",
        },
        "support": {
            "total_resolved":    metric_store.sum("support_ticket_resolved",  period_start, granularity="day"),
            "total_escalated":   metric_store.sum("support_ticket_escalated", period_start, granularity="day"),
            "escalation_rate":   compute_ratio_for_period(
                "support_ticket_escalated", "support_ticket_resolved", period_start
            ),
            "avg_resolution_min": metric_store.avg("support_avg_resolution_minutes", period_start),
        },
        "marketing": {
            "posts_published":  metric_store.sum("posts_published", period_start, granularity="day"),
            "by_channel":       metric_store.get_per_channel("posts_by_channel", period_start),
            "top_channel":      attribution_store.top_channel(period_start),
        },
        "products": {
            "total_active":    product_registry.count_published(),
            "new_this_period": event_store.count_events("NEW_PRODUCT_LIVE", period_start),
            "top_seller":      metric_store.top_by_theme("sales_by_theme", period_start),
            "stagnant":        pattern_store.get_stagnant_products(period_start),
        },
    }
```

---

## ١٦. Owner Critical Alerts

```python
"""
إشارات يجب أن تصل لصاحب المشروع مباشرةً — لا تبقى بين الوكلاء فقط.
"""

OWNER_CRITICAL_SIGNALS = {
    SignalType.SALES_DROP_ALERT,
    SignalType.SUPPORT_SURGE_ALERT,
    SignalType.RECURRING_QUALITY_ISSUE,
    SignalType.RECONCILIATION_MISMATCH,
    SignalType.NO_OUTPUT_ALERT,    # قالب بلا مبيعات 30 يوماً
}


def send_owner_critical_alert(signal: AnalyticsSignal) -> None:
    resend_client.emails.send({
        "from":    STORE_EMAIL_FROM,
        "to":      OWNER_EMAIL,
        "subject": f"تنبيه عاجل — {signal.signal_type.value.replace('_', ' ')}",
        "html":    render_email_template("owner_critical_alert", {
            "signal_type":    signal.signal_type.value,
            "theme_slug":     signal.theme_slug or "عام",
            "recommendation": signal.recommendation,
            "data":           signal.data,
            "generated_at":   signal.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        }),
    })
```

---

## ١٧. Signal Outcome Feedback Loop

```python
"""
يُتيح تحسين الإشارات مستقبلاً:
  - هل أدت الإشارة إلى تحسّن؟
  - أي الإشارات مفيدة وأيها ضجيج؟

في v1: Stub فقط — يُسجَّل ولا يُحسَّب تلقائياً.
مستقبلاً: pattern على نتائج الإشارات لتحسين confidence وthresholds.
"""

class SignalOutcomeTracker:

    def register(self, signal: AnalyticsSignal) -> None:
        """يُسجَّل عند إرسال الإشارة."""
        outcome = SignalOutcome(
            outcome_id          = str(uuid.uuid4()),
            signal_id           = signal.signal_id,
            target_agent        = signal.target_agent,
            action_taken        = None,    # يُملَأ لاحقاً
            observed_metric     = self._get_related_metric(signal.signal_type),
            before_value        = self._get_current_value(signal),
            after_value         = None,    # يُحسَّب بعد outcome_window_days
            outcome_window_days = 7,
            success_score       = None,
            evaluated_at        = None,
            notes               = "registered — pending evaluation",
        )
        outcome_store.save(outcome)

    def evaluate_pending_outcomes(self) -> None:
        """
        يُشغَّل أسبوعياً — يُقيّم الإشارات المرسلة قبل 7 أيام.
        v1: تسجيل القيمة الجديدة فقط.
        """
        pending = outcome_store.get_pending(window_days=7)

        for outcome in pending:
            signal = signal_store.get(outcome.signal_id)
            if not signal:
                continue

            current_value = self._get_current_value(signal)
            outcome.after_value  = current_value
            outcome.evaluated_at = datetime.utcnow()

            if outcome.before_value and current_value:
                # تقييم بسيط: هل تحسّن المقياس؟
                if outcome.before_value > 0:
                    change = (current_value - outcome.before_value) / outcome.before_value
                    outcome.success_score = max(0.0, min(1.0, (change + 1) / 2))

            outcome_store.update(outcome)

    def _get_related_metric(self, signal_type: SignalType) -> Optional[str]:
        mapping = {
            SignalType.NO_OUTPUT_ALERT:     "sales_count",
            SignalType.SALES_DROP_ALERT:    "sales_count",
            SignalType.SUPPORT_SURGE_ALERT: "support_ticket_escalated",
            SignalType.BEST_TIME:           "sales_count",
            SignalType.BEST_CHANNEL:        "sales_by_channel",
        }
        return mapping.get(signal_type)


signal_outcome_tracker = SignalOutcomeTracker()
```

---

## ١٨. Product Registry Dependency

```python
"""
وكيل التحليل يعتمد على Product Registry — read-only.
Source owner: platform_agent.
Analytics يقرأ منه — لا يكتب.

ما يُستخدم:
  - get_all_published(): للكشف عن المنتجات الراكدة
  - get_launch_date(): لحساب أيام بلا مبيعات
  - count_published(): للإحصاءات العامة

ماذا يحدث إن تعارض Registry مع LS؟
  → LS يفوز للبيانات المالية
  → Registry يُستخدم فقط لبيانات الحالة (published/archived)
"""

class ProductRegistryReader:
    """
    واجهة قراءة فقط — لا write أبداً من وكيل التحليل.
    """

    def get_all_published(self) -> List[dict]:
        return db.fetchall(
            "SELECT theme_slug, theme_name_ar, published_at "
            "FROM theme_registry WHERE status = 'published'"
        )

    def get_all_published_slugs(self) -> List[str]:
        rows = db.fetchall("SELECT theme_slug FROM theme_registry WHERE status = 'published'")
        return [r["theme_slug"] for r in rows]

    def get_launch_date(self, theme_slug: str) -> Optional[datetime]:
        row = db.fetchone(
            "SELECT published_at FROM theme_registry WHERE theme_slug = %s",
            [theme_slug]
        )
        return parse_datetime(row["published_at"]) if row else None

    def count_published(self) -> int:
        return db.fetchone("SELECT COUNT(*) as count FROM theme_registry WHERE status='published'")["count"]


product_registry = ProductRegistryReader()
```

---

## ١٩. Idempotency Strategy

```python
def build_event_idempotency_key(event_id: str) -> str:
    return f"analytics_event:{event_id}"


def build_signal_idempotency_key(
    signal_type: SignalType,
    theme_slug:  Optional[str],
    period:      str,
) -> str:
    """إشارات دورية: نفس signal + theme + period لا تُرسَل مرتين."""
    slug_part = theme_slug or "global"
    return f"signal:{signal_type.value}:{slug_part}:{period}"


def signal_sent_recently(
    signal_type:  SignalType,
    theme_slug:   Optional[str],
    hours:        int,
    filter_key:   Optional[str] = None,
) -> bool:
    """يمنع تكرار الإشارات الفورية في نافذة زمنية."""
    since = datetime.utcnow() - timedelta(hours=hours)
    return signal_store.exists_since(signal_type, theme_slug, since, filter_key)
```

---

## ٢٠. Event Contract Schemas

### ANALYTICS_SIGNAL (مُطلَق)

```json
{
  "event_id":      "uuid-v4",
  "event_type":    "ANALYTICS_SIGNAL",
  "event_version": "1.0",
  "source":        "analytics_agent",
  "occurred_at":   "ISO-datetime",
  "correlation_id": "signal:{signal_id}",
  "data": {
    "signal_id":      "sig-uuid",
    "signal_type":    "best_time",
    "theme_slug":     "restaurant_modern",
    "channel":        "facebook",
    "recommendation": "أفضل وقت نشر: 20:00 بتوقيت الرياض",
    "confidence":     0.87,
    "data": {
      "recommended_hour":   20,
      "timezone":           "Asia/Riyadh",
      "based_on_days":      30,
      "attribution_confidence": "low"
    }
  }
}
```

### WEEKLY_REPORT_READY (مُطلَق)

```json
{
  "event_id":      "uuid-v4",
  "event_type":    "WEEKLY_REPORT_READY",
  "event_version": "1.0",
  "source":        "analytics_agent",
  "occurred_at":   "ISO-datetime",
  "correlation_id": "report:weekly:2025-W12",
  "data": {
    "report_id":      "rep-uuid",
    "period_start":   "ISO-datetime",
    "period_end":     "ISO-datetime",
    "total_sales":    15,
    "total_revenue":  435.0,
    "top_theme":      "restaurant_modern",
    "escalation_rate": 0.08,
    "concerns_count": 2
  }
}
```

---

## ٢١. أمان وخصوصية البيانات

```python
ANALYTICS_SECURITY_REQUIREMENTS = [
    "Lemon Squeezy API: قراءة فقط",
    "HelpScout API: قراءة فقط",
    "Product Registry: قراءة فقط",
    "Redis: استماع + نشر إشارات — لا تعديل بيانات",
    "لا customer_id في attribution_records — sale_id فقط",
    "لا بريد عميل في أي إشارة أو تقرير",
    "Dashboard: لصاحب المشروع فقط",
    "وكيل التحليل لا يُغيّر أي بيانات في المنظومة",
    "Attribution confidence مُعلَن دائماً — لا ادعاء دقة زائفة",
]
```

---

## ٢٢. Error Codes Catalog

```python
ANALYTICS_ERROR_CODES = {
    "ANL_EVENT_STORE_FAILED":         "فشل تخزين الحدث",
    "ANL_EVENT_DUPLICATE":            "حدث مكرر — تخطّي",
    "ANL_METRIC_NOT_DEFINED":         "مقياس غير موجود في METRIC_DEFINITIONS",
    "ANL_METRIC_COMPUTE_FAILED":      "فشل حساب مقياس",
    "ANL_METRIC_STORE_FAILED":        "فشل تخزين المقياس",
    "ANL_LS_API_ERROR":               "خطأ في Lemon Squeezy API",
    "ANL_HELPSCOUT_API_ERROR":        "خطأ في HelpScout API",
    "ANL_RECONCILIATION_FAILED":      "فشل مزامنة بيانات LS",
    "ANL_RECONCILIATION_MISMATCH":    "تباين كبير بين LS وRedis",
    "ANL_PATTERN_DETECT_FAILED":      "فشل اكتشاف نمط — جزئي",
    "ANL_PATTERN_STORE_FAILED":       "فشل تخزين النمط",
    "ANL_SIGNAL_GENERATE_FAILED":     "فشل توليد إشارة",
    "ANL_SIGNAL_DISPATCH_FAILED":     "فشل إرسال الإشارة",
    "ANL_SIGNAL_DUPLICATE":           "إشارة مكررة للفترة ذاتها",
    "ANL_REPORT_GENERATE_FAILED":     "فشل توليد التقرير",
    "ANL_REPORT_SEND_FAILED":         "فشل إرسال التقرير",
    "ANL_ATTRIBUTION_FAILED":         "فشل تحديد مصدر البيع",
    "ANL_RETENTION_CLEANUP_FAILED":   "فشل تنظيف البيانات القديمة",
    "ANL_PRODUCT_REGISTRY_READ_FAIL": "فشل قراءة Product Registry",
    "ANL_OUTCOME_EVALUATE_FAILED":    "فشل تقييم نتيجة الإشارة",
}
```

---

## ٢٣. بنية الـ State

```python
class AnalyticsState(TypedDict):
    incoming_event:    Optional[AnalyticsEvent]
    stored_event_id:   Optional[str]
    immediate_signals: List[AnalyticsSignal]
    metrics_period:    Optional[tuple]
    computed_metrics:  List[MetricSnapshot]
    detected_patterns: List[Pattern]
    actionable_patterns: List[Pattern]
    failed_detectors:  List[str]
    generated_signals: List[AnalyticsSignal]
    dispatched_signals: List[str]
    current_report:    Optional[WeeklyReport]
    status:            str
    error_code:        Optional[str]
    logs:              List[str]
```

---

## ٢٤. البيئة المحلية ومتغيرات البيئة

```env
LS_API_KEY=...
HELPSCOUT_API_KEY=...
HELPSCOUT_MAILBOX_ID=...
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/analytics_db
RESEND_API_KEY=...
STORE_EMAIL_FROM=قوالب عربية <hello@ar-themes.com>
OWNER_EMAIL=owner@ar-themes.com

# جدولة
METRICS_BATCH_CRON=0 * * * *
DAILY_AGGREGATION_CRON=5 0 * * *
PATTERN_BATCH_CRON=0 3 * * *
IMMEDIATE_EVALUATOR_CRON=*/15 * * * *
RECONCILIATION_CRON=0 4 * * *
WEEKLY_REPORT_CRON=0 8 * * 0
MONTHLY_REPORT_CRON=0 8 1 * *
RETENTION_CLEANUP_CRON=0 2 * * 0
OUTCOME_EVALUATE_CRON=0 9 * * 0

# Thresholds
NO_SALES_ALERT_DAYS=30
SALES_DROP_THRESHOLD=0.50
SUPPORT_SURGE_THRESHOLD=10
CAMPAIGN_NO_OUTPUT_HOURS=24
ATTRIBUTION_WINDOW_DAYS=7
PATTERN_DECLINE_THRESHOLD=0.30

# Retention
RETENTION_RAW_EVENTS_DAYS=90
RETENTION_METRICS_DAYS=365
RETENTION_PATTERNS_DAYS=180
RETENTION_SIGNALS_DAYS=365
RETENTION_REPORTS_DAYS=730
RETENTION_ATTRIBUTION_DAYS=365

LOG_LEVEL=INFO
```

---

## ٢٥. دستور الوكيل

```markdown
# دستور وكيل التحليل v2

## الهوية
أنا طبقة استخبارات تشغيلية للمنظومة — أرى كل شيء لكن لا أُغيّر شيئاً.
occurred_at هو الوقت الحقيقي. received_at للتشخيص فقط.
Attribution ما أقوله تقريب — أُعلن الثقة دائماً.

## القواعد المطلقة
١. لا أُغيّر أي شيء — أُرسل إشارات فقط
٢. occurred_at للتحليل — received_at للتشخيص
٣. Attribution = تقريب — الثقة مُعلَنة في كل تقرير
٤. Lemon Squeezy مصدر الحقيقة — Redis مكمّل
٥. Immediate Evaluator منفصل عن Event Collector
٦. Metric granularity صريح — لا أسماء مُضلِّلة
٧. escalation_rate من counts — لا جمع rates
٨. الفشل الجزئي لا يوقف Pattern Analyzer
٩. Owner Critical Alerts تصل مباشرةً — لا تبقى بين الوكلاء
١٠. Signal Outcome يُسجَّل — لتحسين الإشارات مستقبلاً

## ما أُجيده
- تجميع الأحداث بـ occurred_at صحيح
- حساب مقاييس بـ granularity محدد وتجميع صحيح
- اكتشاف نمطين: تشغيلي (تنبيهات) وتجاري (قرارات)
- إرسال إشارات للوكلاء الستة بحسب نوعها
- تنبيهات مباشرة لصاحب المشروع للحالات الحرجة
- مزامنة يومية مع Lemon Squeezy للدقة

## ما أتجنبه
- تغيير أي بيانات
- ادعاء دقة Attribution أعلى مما هو فعلي
- تسمية مقياس daily وهو hourly
- حساب rate بجمع rates
- تشغيل Pattern Analyzer على كل حدث
```

---

## ٢٦. قائمة التحقق النهائية

### Event Collector + Immediate Evaluator

```
□ occurred_at من الحدث — ليس received_at
□ idempotency: event_id لا يُخزَّن مرتين
□ attribution عند NEW_SALE: مبني على occurred_at
□ Immediate Evaluator: check_support_surge عند SUPPORT_TICKET_ESCALATED
□ Immediate Evaluator: emit RECURRING_QUALITY_ISSUE لوكيل البناء
□ جدولة no_sales_check بعد 30 يوماً من NEW_PRODUCT_LIVE
□ جدولة campaign_output_check بعد 24 ساعة من CAMPAIGN_LAUNCHED
□ Immediate Evaluator cron كل 15 دقيقة: no_sales + sales_drop + campaign_output
□ idempotency للإشارات الفورية: لا تكرار في 24 ساعة
```

### Metrics Engine (Batch — كل ساعة)

```
□ Hourly metrics فقط لما granularity="hour"
□ وحدة metric من METRIC_DEFINITIONS — لا اسم مُضلِّل
□ الفشل الجزئي لا يوقف العملية
□ Daily aggregation: counts تُجمَّع، rates تُحسَّب من counts
```

### Pattern Analyzer (Batch — يومياً)

```
□ Operational detectors + Business detectors
□ الفشل الجزئي: يُسجَّل ويكمل
□ detect_stagnant_products: Batching — لا N+1 queries
□ channel_performance: confidence مخفَّض لـ Attribution تقريبي
□ الأنماط القابلة للتنفيذ تُولّد إشارات
```

### Signal Generator

```
□ كل إشارة في SIGNAL_ROUTING
□ OWNER_CRITICAL_SIGNALS تصل لصاحب المشروع + الوكيل
□ signal_outcome_tracker.register لكل إشارة
□ ANALYTICS_SIGNAL بالصيغة الموحدة
□ attribution_confidence مُعلَن في الإشارات المرتبطة
```

### Report Generator

```
□ escalation_rate = escalated_count / resolved_count — من counts
□ كل المقاييس مبنية على occurred_at
□ highlights وconcerns من Pattern Analyzer
□ Attribution note في كل metric مرتبط
□ WEEKLY_REPORT_READY حدث على Redis
□ تقرير مُرسَل لصاحب المشروع
```

### Reconciliation + Retention

```
□ LS Reconciliation يومياً — occurs_at للمقارنة
□ تباين > 5 سجلات → RECONCILIATION_MISMATCH لصاحب المشروع
□ Retention cleanup أسبوعياً — لا حذف دون Policy
□ Signal Outcome evaluation أسبوعياً
□ Product Registry: قراءة فقط — لا write
```

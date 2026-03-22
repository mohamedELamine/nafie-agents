# منصة نافع — وثيقة المنظومة الجامعة
## المرجع التنفيذي الشامل v2

> هذه النسخة تجمع v1 + التصحيحات المعمارية الكاملة.
> تُعدّ المرجع الأم الذي تُشتق منه بقية العقود التنفيذية.

---

## فهرس المحتويات

1. نظرة عليا — ما هي منصة نافع؟
2. خريطة المنظومة الكاملة
3. طبقات المنظومة — تصنيف الكيانات
4. الوكلاء الثمانية — جدول مرجعي
5. Blocking vs Non-blocking — تصنيف التشغيل
6. تسلسل التبعيات — النموذج المحسوم
7. State Ownership Matrix — من يملك الحقيقة؟
8. قنوات Redis — CHANNEL ARCHITECTURE
9. Event Delivery Policy — سياسة التسليم
10. فهرس الأحداث الكاملة
11. عقد الحدث الموحّد — Event Envelope
12. خريطة تدفق الأحداث
13. Workflows المركّبة
14. Compensation / Rollback Matrix
15. Lifecycle State Machines
16. USER_LOCKED_DECISIONS
17. البنية التحتية المشتركة
18. قائمة الوثائق المرجعية

---

## ١. نظرة عليا — ما هي منصة نافع؟

### الفكرة

**نافع** منصة متكاملة لإنتاج قوالب WordPress عربية احترافية وبيعها، تعمل بمنظومة وكلاء ذكاء اصطناعي تُنتج القوالب، تُسوّق لها، تدعم عملاءها، وتحلّل أداءها.

### المبدأ الجوهري

```
صاحب المشروع يُقرّر الاستراتيجية.
المنظومة تُنفّذ التشغيل.
الأحداث وسيلة إشعار — قواعد البيانات مصدر الحقيقة.
```

### ما تفعله المنظومة تلقائياً

```
بناء قوالب WordPress عربية احترافية
    ↓ (بعد موافقة صاحب المشروع)
توليد أصول بصرية كاملة (صور + فيديو)
    ↓ (بعد موافقة صاحب المشروع)
إنتاج نصوص صفحة المنتج والتسويق
    ↓
نشر القالب على المتجر
    ↓ (بعد موافقة صاحب المشروع على صفحة المنتج)
بناء قاعدة معرفة للدعم تلقائياً
    ↓
إطلاق حملة تسويقية على القنوات الرقمية
    ↓
دعم العملاء على مدار الساعة
    ↓
تحليل الأداء وإرسال إشارات للتحسين
```

---

## ٢. خريطة المنظومة الكاملة

```
┌─────────────────────────────────────────────────────────┐
│                   صاحب المشروع                           │
│           (قرارات استراتيجية + موافقات)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  وكيل المشرف                             │
│   (تنسيق + صحة + سياسات + حل التعارضات)                │
└────┬────┬────┬────┬────┬────┬────┬─────────────────────┘
     │    │    │    │    │    │    │
     ▼    ▼    ▼    ▼    ▼    ▼    ▼
  بناء  بصري منصة  دعم  محتوى تسويق تحليل
     │    │    │    │    │    │    │
     └────┴────┴────┴────┴────┴────┘
                    │
              Redis Pub/Sub
           (إشعارات + تنسيق)
            +
         Redis Streams
       (أحداث الأعمال الحرجة)
```

### قاعدة التواصل

```
كل وكيل ← يستمع لأحداث على قناته
كل وكيل → يُطلق أحداثاً على Redis
لا وكيل يستدعي وكيلاً آخر مباشرةً
الأحداث إشعارات — قواعد البيانات مصدر الحقيقة
```

---

## ٣. طبقات المنظومة — تصنيف الكيانات

```
طبقة أولى — وكلاء تشغيلية (Operational Agents)
──────────────────────────────────────────────
  وكيل البناء
  وكيل الإنتاج البصري
  وكيل المنصة
  وكيل الدعم
  وكيل المحتوى
  وكيل التسويق
  وكيل التحليل

طبقة ثانية — وكيل التنسيق (Coordination Layer)
────────────────────────────────────────────────
  وكيل المشرف
  (ليس وكيل تنفيذ — وكيل تنسيق وحوكمة)

طبقة ثالثة — عقود الحوكمة (Governance Contracts)
──────────────────────────────────────────────────
  Brand Constitution   ← صوت المتجر الموحّد
  USER_LOCKED_DECISIONS ← القرارات المحجوزة
  Global Policy Layer  ← ميزانية + حدود + أولويات
```

### ملاحظة: visual_audio_agent

```
ليس وكيلاً مستقلاً.
هو Workflow Phase داخل وكيل الإنتاج البصري.
يُنظَّم عبر وكيل الإنتاج البصري مباشرةً.
```

---

## ٤. الوكلاء الثمانية — جدول مرجعي

| # | الوكيل | الدور | القناة | التصنيف التشغيلي | الوثيقة |
|---|--------|-------|--------|-----------------|---------|
| ١ | وكيل البناء | إنتاج قوالب WordPress | `builder_events` | Blocking | final.md |
| ٢ | وكيل الإنتاج البصري | صور + فيديو | `visual_events` | Conditionally Blocking | visual_production_v2.md |
| ٣ | وكيل المنصة | متجر + تراخيص + نشر | `platform_events` | Blocking | platform_agent_v3.md |
| ٤ | وكيل الدعم | دعم عملاء + KB | `support_events` | Post-launch Non-blocking | support_agent_v3.md |
| ٥ | وكيل المحتوى | نصوص + محتوى | `content_events` | Blocking (pre-launch) | content_agent_v2.md |
| ٦ | وكيل التسويق | نشر + حملات | `marketing_events` | Post-launch Non-blocking | marketing_agent_v2.md |
| ٧ | وكيل التحليل | قياس + إشارات | `analytics_events` | Async Optional | analytics_agent_v2.md |
| ٨ | وكيل المشرف | تنسيق + صحة + سياسات | `supervisor_events` | Coordination Critical | supervisor_agent_v2.md |

---

## ٥. Blocking vs Non-blocking — تصنيف التشغيل

```python
AGENT_BLOCKING_CLASSIFICATION = {

    "builder_agent": {
        "classification": "Blocking",
        "meaning":        "فشله يوقف الإطلاق كلياً",
        "launch_required": True,
    },

    "visual_production_agent": {
        "classification": "Conditionally Blocking",
        "meaning":        "إن فشل كلياً → placeholder assets + إطلاق",
                           "إن فشلت أصول إلزامية → يوقف الإطلاق",
        "launch_required": "partial",
        "fallback":        "launch_with_placeholder_assets",
    },

    "platform_agent": {
        "classification": "Blocking",
        "meaning":        "فشله يوقف النشر كلياً",
        "launch_required": True,
    },

    "content_agent": {
        "classification": "Blocking (pre-launch)",
        "meaning":        "CONTENT_READY شرط لـ NEW_PRODUCT_LIVE",
                           "فشله يؤخر الإطلاق حتى الإصلاح أو المحتوى الافتراضي",
        "launch_required": True,
        "fallback":        "use_default_content_template",
    },

    "support_agent": {
        "classification": "Post-launch Non-blocking",
        "meaning":        "الإطلاق يكمل بدونه، KB تُبنى لاحقاً",
        "launch_required": False,
    },

    "marketing_agent": {
        "classification": "Post-launch Non-blocking",
        "meaning":        "الإطلاق يكمل بدونه، الحملة تُؤجَّل",
        "launch_required": False,
    },

    "analytics_agent": {
        "classification": "Async Optional",
        "meaning":        "لا يؤثر على الإطلاق بأي حال",
        "launch_required": False,
    },

    "supervisor_agent": {
        "classification": "Coordination Critical",
        "meaning":        "لا ينفّذ لكن يُنسّق، Workflows تعمل بدونه في حالة الطوارئ",
        "launch_required": False,
    },
}
```

---

## ٦. تسلسل التبعيات — النموذج المحسوم

### القرار المعماري: النموذج A — المحتوى قبل الإطلاق

```
المحتوى يُنتج قبل النشر على المتجر.
CONTENT_READY + THEME_ASSETS_READY شرطان لـ NEW_PRODUCT_LIVE.
```

### لماذا هذا القرار؟

```
صفحة المنتج تحتاج نصاً احترافياً قبل أن تُنشر.
النشر بصفحة فارغة أو بمحتوى افتراضي يضر بالمبيعات.
وكيل المحتوى يبدأ من THEME_APPROVED مباشرةً — لا ينتظر NEW_PRODUCT_LIVE.
```

### المستويات الأربعة

```
المستوى الأول — يعمل مستقلاً:
  وكيل البناء        ← يحتاج: THEME_CONTRACT فقط
  وكيل المشرف        ← يحتاج: Redis فقط

المستوى الثاني — يحتاج THEME_APPROVED:
  وكيل الإنتاج البصري ← يبدأ من THEME_APPROVED
  وكيل المحتوى        ← يبدأ من THEME_APPROVED

المستوى الثالث — يحتاج المستوى الثاني:
  وكيل المنصة ← يحتاج: THEME_ASSETS_READY + CONTENT_READY معاً

المستوى الرابع — يحتاج NEW_PRODUCT_LIVE:
  وكيل الدعم    ← يبدأ بناء KB
  وكيل التسويق  ← يطلق الحملة
  وكيل التحليل  ← يسجّل الإطلاق
```

### ترتيب البناء التقني الموصى به

```
١. وكيل البناء          ← القلب — كل شيء يبدأ منه
٢. وكيل المنصة          ← يُطلق المنتج
٣. وكيل الدعم           ← يخدم العميل فور الشراء
٤. وكيل الإنتاج البصري ← يُكمل صفحة المنتج
٥. وكيل المحتوى         ← يكتب النصوص
٦. وكيل التسويق         ← يُطلق الحملات
٧. وكيل التحليل         ← يقيس ويُحسّن
٨. وكيل المشرف          ← يُنسّق الكل
```

---

## ٧. State Ownership Matrix — من يملك الحقيقة؟

```python
"""
الأحداث إشعارات.
قواعد البيانات مصدر الحقيقة.
لكل حالة عمل مالك schema واحد فقط.
"""

STATE_OWNERSHIP = {

    "theme_lifecycle": {
        "owner":   "builder schema",
        "states":  ["draft", "built", "review_requested",
                    "approved", "rejected", "launched", "updated", "archived"],
        "source_of_truth": "builder.themes table",
        "event_is":        "notification only",
    },

    "asset_lifecycle": {
        "owner":   "visual schema",
        "states":  ["generation_started", "candidates_ready",
                    "review_requested", "approved", "partially_approved",
                    "rejected", "published", "archived"],
        "source_of_truth": "visual.production_batches + visual.produced_assets",
        "event_is":        "notification only",
    },

    "product_publication_state": {
        "owner":   "platform schema",
        "states":  ["draft", "pending_content", "pending_review",
                    "live", "paused", "archived"],
        "source_of_truth": "platform.product_registry table",
        "event_is":        "notification only",
    },

    "license_state": {
        "owner":   "platform schema",
        "states":  ["issued", "active", "expired", "revoked"],
        "source_of_truth": "platform.licenses table",
        "primary_source":  "Lemon Squeezy API (يفوز عند التعارض)",
        "event_is":        "notification only",
    },

    "sale_state": {
        "owner":   "platform schema + analytics schema",
        "states":  ["completed", "refunded"],
        "source_of_truth": "Lemon Squeezy API (المصدر الأول)",
        "secondary":       "platform.sales table",
        "event_is":        "notification only",
    },

    "knowledge_base_state": {
        "owner":   "support schema",
        "states":  ["pending", "draft", "published", "archived"],
        "source_of_truth": "support.knowledge_articles + HelpScout Docs",
        "event_is":        "notification only",
    },

    "content_piece_state": {
        "owner":   "content schema",
        "states":  ["requested", "generating", "validating",
                    "awaiting_review", "ready", "failed"],
        "source_of_truth": "content.content_pieces table",
        "event_is":        "notification only",
    },

    "campaign_state": {
        "owner":   "marketing schema",
        "states":  ["planned", "active", "paused", "completed", "cancelled"],
        "source_of_truth": "marketing.campaigns table",
        "event_is":        "notification only",
    },

    "workflow_state": {
        "owner":   "supervisor schema",
        "states":  ["pending", "running", "waiting", "paused",
                    "completed", "failed", "cancelled"],
        "source_of_truth": "supervisor.workflow_instances table",
        "event_is":        "trigger + notification",
    },

    "metrics_signals": {
        "owner":   "analytics schema",
        "states":  ["collected", "processed", "signaled"],
        "source_of_truth": "analytics.metric_snapshots + analytics.signals",
        "event_is":        "notification only",
    },
}
```

---

## ٨. قنوات Redis — CHANNEL ARCHITECTURE

### نموذج هجين: Pub/Sub + Streams

```python
"""
Redis Pub/Sub: للإشعارات اللحظية غير الحرجة
Redis Streams: للأحداث الحرجة القابلة لإعادة التشغيل

السبب: Pub/Sub لا يضمن delivery عند فشل المستهلك.
Streams يُعيد التشغيل ويدعم consumer groups.
"""

CHANNEL_ARCHITECTURE = {

    # أحداث الأعمال الحرجة → Redis Streams
    "CRITICAL_STREAMS": {
        "theme-events":    ["THEME_APPROVED", "THEME_UPDATED"],
        "asset-events":    ["THEME_ASSETS_READY", "THEME_ASSETS_PARTIALLY_READY"],
        "product-events":  ["NEW_PRODUCT_LIVE", "THEME_UPDATED_LIVE"],
        "sales-events":    ["NEW_SALE", "LICENSE_ISSUED"],
        "workflow-events": ["WORKFLOW_START", "WORKFLOW_CANCEL", "WORKFLOW_FAILED"],
    },

    # إشعارات + تنسيق → Pub/Sub
    "PUBSUB_CHANNELS": {
        "builder_events":      "أحداث وكيل البناء",
        "visual_events":       "أحداث الإنتاج البصري",
        "platform_events":     "أحداث المنصة",
        "support_events":      "أحداث الدعم",
        "content_events":      "أحداث المحتوى",
        "marketing_events":    "أحداث التسويق",
        "analytics_events":    "أحداث التحليل",
        "supervisor_events":   "أحداث المشرف",
        "heartbeat_events":    "نبضات حياة الوكلاء",
        "audit_events":        "سجل تدقيق المشرف",
    },
}

# قاعدة الاختيار:
# حدث حرج (يؤثر على إطلاق أو بيع) → Redis Streams
# إشعار أو تنسيق → Pub/Sub
```

---

## ٩. Event Delivery Policy — سياسة التسليم

```python
EVENT_DELIVERY_POLICY = """
١. كل أحداث الأعمال الحرجة: at-least-once delivery
٢. كل المستهلكين يجب أن ينفّذوا idempotent handlers
   (نفس الحدث مرتين = نفس النتيجة)
٣. إعادة المحاولة للأحداث الحرجة:
   - محاولة ١: فوراً
   - محاولة ٢: بعد 30 ثانية
   - محاولة ٣: بعد 60 ثانية
   - بعد ٣ محاولات: dead-letter stream + AGENT_FAILED event
٤. وكيل المشرف يفتح Recovery Workflow عند فشل سلسلة حرجة
٥. Pub/Sub: best-effort (لا retry — للإشعارات فقط)
"""

IDEMPOTENCY_RULES = {
    "كل وكيل": "يحمل idempotency_key في كل عملية",
    "نفس الحدث مرتين": "يُتجاهَل إن وُجد السجل مسبقاً",
    "مفتاح idempotency": "مُشتق من business context (ليس event_id فقط)",
}

DEAD_LETTER_POLICY = {
    "بعد": "3 محاولات فاشلة",
    "يُرسَل إلى": "dead_letter_stream",
    "يُبلَّغ": "وكيل المشرف + صاحب المشروع",
    "الإجراء": "تدخل يدوي أو Recovery Workflow",
}
```

---

## ١٠. فهرس الأحداث الكاملة

### عقد الحدث الموحّد (راجع القسم ١١ للتفاصيل)

#### أحداث وكيل البناء

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `THEME_BUILT` | builder_events | Pub/Sub | supervisor |
| `THEME_APPROVED` | theme-events | **Stream** | visual, content, supervisor |
| `THEME_UPDATED` | theme-events | **Stream** | visual, platform, supervisor |
| `BUILD_FAILED` | builder_events | Pub/Sub | supervisor |

#### أحداث وكيل الإنتاج البصري

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `THEME_ASSETS_READY` | asset-events | **Stream** | platform, marketing, supervisor |
| `THEME_ASSETS_PARTIALLY_READY` | asset-events | **Stream** | platform, marketing |
| `THEME_ASSETS_UPDATED` | asset-events | **Stream** | platform |
| `THEME_ASSETS_FAILED` | visual_events | Pub/Sub | supervisor |
| `THEME_ASSETS_REVIEW_REQUESTED` | visual_events | Pub/Sub | owner |

#### أحداث وكيل المنصة

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `NEW_PRODUCT_LIVE` | product-events | **Stream** | support, marketing, content, analytics |
| `THEME_UPDATED_LIVE` | product-events | **Stream** | content, analytics |
| `NEW_SALE` | sales-events | **Stream** | analytics |
| `LICENSE_ISSUED` | sales-events | **Stream** | analytics |
| `LAUNCH_FAILED` | platform_events | Pub/Sub | supervisor |

#### أحداث وكيل الدعم

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `SUPPORT_TICKET_RESOLVED` | support_events | Pub/Sub | analytics |
| `SUPPORT_TICKET_ESCALATED` | support_events | Pub/Sub | analytics |
| `RECURRING_ISSUE_DETECTED` | support_events | Pub/Sub | content, analytics |
| `KNOWLEDGE_BASE_UPDATED` | support_events | Pub/Sub | supervisor |

#### أحداث وكيل المحتوى

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `CONTENT_READY` | content_events | Pub/Sub | platform, marketing |
| `CONTENT_PRODUCED` | content_events | Pub/Sub | analytics |
| `CONTENT_REQUEST` | content_events | Pub/Sub | content |

#### أحداث وكيل التسويق

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `CAMPAIGN_LAUNCHED` | marketing_events | Pub/Sub | analytics, supervisor |
| `POST_PUBLISHED` | marketing_events | Pub/Sub | analytics |

#### أحداث وكيل التحليل

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `ANALYTICS_SIGNAL` | analytics_events | Pub/Sub | marketing, content, platform, builder, support |
| `WEEKLY_REPORT_READY` | analytics_events | Pub/Sub | owner |

#### أحداث وكيل المشرف

| الحدث | القناة | النوع | المستمعون |
|-------|--------|-------|-----------|
| `WORKFLOW_START` | workflow-events | **Stream** | الوكيل المعني |
| `WORKFLOW_CANCEL` | workflow-events | **Stream** | الوكيل المعني |
| `WORKFLOW_COMPLETED` | supervisor_events | Pub/Sub | — |
| `WORKFLOW_FAILED` | supervisor_events | Pub/Sub | owner |
| `AGENT_PAUSE` | supervisor_events | Pub/Sub | الوكيل المعني |
| `AGENT_RESUME` | supervisor_events | Pub/Sub | الوكيل المعني |
| `AGENT_HEARTBEAT` | heartbeat_events | Pub/Sub | supervisor |
| `SYSTEM_ALERT` | supervisor_events | Pub/Sub | owner |
| `POLICY_UPDATE` | supervisor_events | Pub/Sub | كل الوكلاء |

---

## ١١. عقد الحدث الموحّد — Event Envelope

```json
{
  "event_id":        "uuid-v4",
  "event_type":      "THEME_APPROVED",
  "event_version":   "1.0",
  "source":          "builder_agent",
  "occurred_at":     "2026-03-16T12:00:00Z",
  "correlation_id":  "launch:restaurant_modern:20260316-0001",
  "causation_id":    "uuid-of-parent-event",
  "business_key":    "theme:restaurant_modern:20260316-0001",
  "idempotency_key": "theme_approved:restaurant_modern:20260316-0001",
  "trace_id":        "trace-uuid",
  "retry_count":     0,
  "data":            { }
}
```

### الحقول الإلزامية

| الحقل | الوصف | مثال |
|-------|-------|------|
| `event_id` | معرّف فريد للحدث | uuid-v4 |
| `event_type` | نوع الحدث | THEME_APPROVED |
| `event_version` | إصدار schema الحدث | "1.0" |
| `source` | الوكيل المُطلِق | builder_agent |
| `occurred_at` | وقت وقوع الحدث (ليس الاستلام) | ISO-datetime |
| `correlation_id` | معرّف الرحلة الكاملة | launch:slug:version |
| `business_key` | المفتاح العملي للـ idempotency | theme:slug:version |

### الحقول المستحسنة

| الحقل | الوصف |
|-------|-------|
| `causation_id` | الحدث الذي تسبّب في هذا الحدث |
| `idempotency_key` | مفتاح منع التكرار في المستهلك |
| `trace_id` | للتتبع عبر وكلاء متعددة |
| `retry_count` | عدد مرات الإعادة (يبدأ من 0) |

---

## ١٢. خريطة تدفق الأحداث

### تدفق إطلاق قالب جديد — النموذج المحسوم

```
صاحب المشروع يعتمد القالب
    │
    ▼
THEME_APPROVED (Stream)
    │
    ├──► وكيل الإنتاج البصري
    │    (يُنتج الأصول + مراجعة بشرية)
    │         │
    │         ▼
    │    THEME_ASSETS_READY (Stream)
    │         │
    │         ▼
    │    وكيل المنصة ◄──────────────────┐
    │    (ينتظر الاثنين معاً)            │
    │                                    │
    └──► وكيل المحتوى                   │
         (يُنتج صفحة المنتج + EMAIL_LAUNCH + MARKETING_COPY)
              │
              ▼
         CONTENT_READY (Pub/Sub)
              │
              └──────────────────────────┘
                         │
                         ▼
                    وكيل المنصة
                    (اكتملت الشروط)
                         │
                         ▼
                    NEW_PRODUCT_LIVE (Stream)
                         │
                         ├──► وكيل الدعم      → KNOWLEDGE_BASE_UPDATED
                         ├──► وكيل التسويق    → CAMPAIGN_LAUNCHED
                         │         │
                         │         ▼
                         │    POST_PUBLISHED (×n)
                         │
                         └──► وكيل التحليل   (يستمع ويسجّل)
```

### تدفق تحديث قالب موجود

```
THEME_UPDATED (Stream)
    │
    ├──► وكيل الإنتاج البصري (أصول متأثرة فقط)
    │    (بحسب Asset Versioning)
    │         │
    │         ▼
    │    THEME_ASSETS_UPDATED (Stream)
    │
    ├──► وكيل المحتوى (بريد التحديث)
    │         │
    │         ▼
    │    CONTENT_READY (email_update)
    │
    └──► وكيل المنصة
              (ينتظر ما يحتاجه ثم يُحدِّث)
              │
              ▼
         THEME_UPDATED_LIVE (Stream)
              │
              └──► وكيل التحليل + وكيل الدعم (إن تغيّرت الميزات)
```

### تدفق طلب دعم عميل

```
عميل ← HelpScout أو Messenger
    │
    ▼
وكيل الدعم
    ├── حُلّ تلقائياً → SUPPORT_TICKET_RESOLVED → analytics
    ├── صُعِّد → SUPPORT_TICKET_ESCALATED → analytics + owner
    └── 3+ مرات → RECURRING_ISSUE_DETECTED
              ├──► content_agent (مقالة معرفة)
              └──► analytics_agent (إشارة لوكيل البناء)
```

### تدفق إشارة التحليل

```
ANALYTICS_SIGNAL
    ├──► marketing_agent  ← best_time, best_channel, low_sales
    ├──► content_agent    ← content_performance
    ├──► platform_agent   ← pricing_signal, product_signal
    ├──► builder_agent    ← build_feedback, quality_issue
    └──► support_agent    ← support_pattern
```

---

## ١٣. Workflows المركّبة

### Workflow إطلاق قالب — THEME_LAUNCH

```
المُشغِّل: THEME_APPROVED (Stream)
المُنسِّق: وكيل المشرف
المهلة:   240 دقيقة

┌─────────────────────────────────────────────────────────┐
│ Step │ الوكيل       │ مُشغَّل بـ       │ ينتهي بـ              │ Blocking │ Timeout  │ عند الفشل    │
├─────────────────────────────────────────────────────────┤
│  1   │ builder      │ يدوي             │ THEME_APPROVED         │ Yes      │ يدوي     │ fail        │
│  2   │ visual       │ THEME_APPROVED   │ THEME_ASSETS_READY     │ Partial  │ 120 دق   │ retry→skip  │
│  3   │ content      │ THEME_APPROVED   │ CONTENT_READY          │ Yes      │ 60 دق    │ fallback    │
│  4   │ platform     │ ASSETS+CONTENT   │ NEW_PRODUCT_LIVE       │ Yes      │ 60 دق    │ retry→fail  │
│  5   │ support      │ NEW_PRODUCT_LIVE │ KNOWLEDGE_BASE_UPDATED │ No       │ 30 دق    │ skip        │
│  6   │ marketing    │ NEW_PRODUCT_LIVE │ CAMPAIGN_LAUNCHED      │ No       │ 30 دق    │ skip        │
│  7   │ analytics    │ NEW_PRODUCT_LIVE │ fire-and-forget        │ No       │ —        │ skip        │
└─────────────────────────────────────────────────────────┘

الخطوتان 5 و6 و7 تعمل بالتوازي (parallel_group: post_launch)
```

### Workflow تحديث قالب — THEME_UPDATE

```
المُشغِّل: THEME_UPDATED (Stream)
المهلة:   120 دقيقة

Step 1: platform ← THEME_UPDATED → THEME_UPDATED_LIVE (Blocking, 30 دق)
Step 2: visual  ← THEME_UPDATED → THEME_ASSETS_UPDATED (Optional, شرطي, 60 دق)
Step 3: content ← THEME_UPDATED → CONTENT_READY/email_update (Non-blocking, 30 دق)
```

---

## ١٤. Compensation / Rollback Matrix

```python
"""
ماذا يحدث عند فشل كل سيناريو؟
"""

COMPENSATION_MATRIX = {

    "launch_failed_before_live": {
        "scenario":     "فشل نشر القالب قبل NEW_PRODUCT_LIVE",
        "owner":        "platform_agent",
        "compensation": [
            "وسم المنتج في platform.product_registry كـ draft",
            "LAUNCH_FAILED event → supervisor",
            "إشعار صاحب المشروع",
        ],
        "data_state":   "draft — لا يُرى من العملاء",
    },

    "license_failed_after_sale": {
        "scenario":     "فشل إصدار الترخيص بعد إتمام البيع",
        "owner":        "platform_agent",
        "compensation": [
            "retry issuance ×3",
            "إن فشلت: إشعار عاجل لصاحب المشروع",
            "إصدار يدوي من Lemon Squeezy",
            "البيع محفوظ — الترخيص معلَّق",
        ],
        "data_state":   "sale=completed, license=pending_manual",
    },

    "assets_failed_after_launch": {
        "scenario":     "اكتُشف خطأ في الأصول بعد النشر",
        "owner":        "visual_production_agent + platform_agent",
        "compensation": [
            "العودة للأصول المعتمدة السابقة من visual.archived",
            "THEME_ASSETS_UPDATED event بالأصول القديمة",
            "إشعار صاحب المشروع",
        ],
        "data_state":   "product=live بأصول سابقة",
    },

    "campaign_launched_for_broken_product": {
        "scenario":     "أُطلقت حملة ثم اكتُشف خطأ حرج في المنتج",
        "owner":        "supervisor_agent",
        "compensation": [
            "AGENT_PAUSE → marketing_agent",
            "SYSTEM_ALERT → owner",
            "تجميد الحملة حتى الحسم اليدوي",
        ],
        "data_state":   "campaign=paused, product=under_review",
    },

    "content_failed_before_launch": {
        "scenario":     "فشل وكيل المحتوى قبل الإطلاق",
        "owner":        "content_agent + supervisor_agent",
        "compensation": [
            "محاولة استخدام default_content_template",
            "إن لم يتوفر: تأخير الإطلاق + إشعار صاحب المشروع",
        ],
        "data_state":   "launch=delayed أو launched_with_default_content",
    },

    "workflow_timed_out": {
        "scenario":     "Workflow تجاوز الحد الزمني",
        "owner":        "supervisor_agent",
        "compensation": [
            "retry الخطوة الفاشلة (إن retry مسموح)",
            "إن استُنفد: WORKFLOW_FAILED + إشعار صاحب المشروع",
            "المنظومة تبقى في last consistent state",
        ],
        "data_state":   "يعتمد على الخطوة الفاشلة",
    },
}
```

---

## ١٥. Lifecycle State Machines

### القالب — Theme Lifecycle

```
draft
  │ (بناء مكتمل)
  ▼
built
  │ (طلب مراجعة)
  ▼
review_requested
  │                   │
  ▼ (موافقة)          ▼ (رفض)
approved           rejected → draft (لإعادة البناء)
  │
  ▼ (نشر ناجح)
launched
  │ (تحديث)
  ▼
updated → launched
  │ (إيقاف)
  ▼
archived
```

### الأصول البصرية — Asset Lifecycle

```
generation_started
  │ (اكتمل الإنتاج)
  ▼
candidates_ready
  │ (اختيار وإرسال للمراجعة)
  ▼
review_requested
  │                        │                    │
  ▼ (موافقة كاملة)          ▼ (موافقة جزئية)     ▼ (رفض)
approved              partially_approved     rejected
  │                        │
  ▼                        ▼
published            published (partial)
  │ (إصدار أحدث)
  ▼
archived (90 يوم)
```

### الـ Workflow — Workflow Lifecycle

```
pending
  │ (بدء التشغيل)
  ▼
running
  │           │           │
  ▼           ▼           ▼
waiting     paused      completed (نهائي)
  │           │
  ▼           ▼ (استئناف)
running ←── running
  │
  ▼ (فشل)
failed (نهائي) ← retry = instance جديدة
  │
  ▼ (إلغاء)
cancelled (نهائي)
```

---

## ١٦. USER_LOCKED_DECISIONS — القرارات المحجوزة

```python
USER_LOCKED_DECISIONS = [
    # تجاري
    "تغيير أسعار المنتجات",
    "إطلاق عروض أو خصومات",
    "إنفاق في الإعلانات المدفوعة",

    # تسويقي
    "تغيير جمهور الإعلانات",
    "الرد على أزمات السمعة",
    "إيقاف حملة جارية",

    # موافقات رسمية
    "اعتماد القالب (THEME_APPROVAL)",
    "اعتماد الأصول البصرية (VISUAL_REVIEW)",
    "اعتماد صفحة المنتج الكاملة (PRODUCT_PAGE_REVIEW)",

    # بيانات وأمان
    "حذف منتجات منشورة",
    "إجراء استرجاعات مالية",
    "تعديل سياسات الأمان",
    "تصدير بيانات العملاء",
]

# لا وكيل ولا مشرف يمس هذه القرارات
# حتى في حالات الطوارئ القصوى
```

---

## ١٧. البنية التحتية المشتركة

### قواعد البيانات

```sql
-- PostgreSQL — قاعدة واحدة، schemas منفصلة
CREATE SCHEMA builder;    -- بيانات بناء القوالب
CREATE SCHEMA visual;     -- batches, assets, manifests
CREATE SCHEMA platform;   -- product_registry, sales, licenses
CREATE SCHEMA support;    -- tickets, knowledge_articles
CREATE SCHEMA content;    -- content_registry, content_pieces
CREATE SCHEMA marketing;  -- campaigns, scheduled_posts
CREATE SCHEMA analytics;  -- events, metrics, signals
CREATE SCHEMA supervisor; -- workflows, conflicts, audit_log
```

### Redis

```
Pub/Sub: إشعارات + تنسيق + heartbeat
Streams: أحداث الأعمال الحرجة (راجع القسم ٨)

مفاتيح Cache:
  heartbeat:{agent_name}        ← نبضة حياة
  idempotency:{key}             ← منع التكرار
  workflow:{business_key}       ← حالة Workflow نشط
```

### التخزين

```
/var/assets/{theme_slug}/{version}/
    candidates/   ← مؤقت (7 أيام)
    review/       ← للمراجعة
    approved/     ← نهائي + manifest.json
    archived/     ← إصدارات قديمة (90 يوم)

/var/assets/placeholders/
    hero_default.webp
    thumb_default.webp
    screenshot_default.png
```

### APIs الخارجية

```
Lemon Squeezy    ← مدفوعات + تراخيص (source of truth للمبيعات)
HelpScout        ← تذاكر الدعم (source of truth للتذاكر)
Resend           ← البريد الإلكتروني
WordPress REST   ← نشر القوالب والصفحات
Facebook/Meta    ← نشر + إعلانات
TikTok           ← نشر
WhatsApp Business ← إشعارات
Replicate/Flux   ← صور
Ideogram         ← صور بنص عربي
Kling AI         ← فيديو
Pika Labs        ← فيديو
Claude API       ← توليد محتوى + تحقق + فحص جودة
```

### متغيرات البيئة المشتركة

```env
# قاعدة بيانات
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379

# البريد
RESEND_API_KEY=...
STORE_EMAIL_FROM=نافع <hello@nafic.com>
OWNER_EMAIL=...

# المتجر
STORE_URL=https://nafic.com
ASSETS_BASE_URL=https://nafic.com/assets
ASSETS_BASE_PATH=/var/assets

# Lemon Squeezy
LS_API_KEY=...
LS_STORE_ID=...
LS_WEBHOOK_SECRET=...

# Claude
CLAUDE_API_KEY=sk-ant-...
```

---

## ١٨. قائمة الوثائق المرجعية

| الوكيل | الوثيقة | الحالة |
|--------|---------|--------|
| وكيل البناء | `final.md` | ✅ مكتملة |
| وكيل الإنتاج البصري | `visual_production_agent_v2.md` | ✅ مكتملة |
| وكيل المنصة | `platform_agent_v3.md` | ✅ مكتملة |
| وكيل الدعم | `support_agent_v3.md` | ✅ مكتملة |
| وكيل المحتوى | `content_agent_v2.md` + `patch_v2_1.md` | ✅ مكتملة |
| وكيل التسويق | `marketing_agent_v2.md` | ✅ مكتملة |
| وكيل التحليل | `analytics_agent_v2.md` | ✅ مكتملة |
| وكيل المشرف | `supervisor_agent_v2.md` | ✅ مكتملة |
| Brand Constitution | `content_agent_v2.md §3` | ✅ مكتملة |
| **هذه الوثيقة** | `nafic_system_overview_v2.md` | ✅ مكتملة |

---

*منصة نافع — وثيقة المنظومة الجامعة v2*
*آخر تحديث: مارس 2026*

# Data Model — Platform Agent

**Source**: `plan.md` Phase 1 | **Date**: 2026-03-22
**Migration**: `db/migrations/001_initial.sql`

---

## Entities

### 1. ThemeRecord (theme_registry)

المرجع الوحيد لحالة القوالب المنشورة — Single Source of Truth.

```
ThemeRecord
├── theme_slug          TEXT  PK          -- مفتاح العمل الأساسي (e.g. "tayseer")
├── theme_name_ar       TEXT  NOT NULL    -- الاسم العربي للعرض
├── wp_post_id          INT   UNIQUE      -- معرّف WordPress (من هنا فقط)
├── wp_post_url         TEXT              -- رابط صفحة المنتج
├── ls_product_id       TEXT  UNIQUE      -- معرّف منتج Lemon Squeezy
├── ls_single_variant   TEXT              -- variant_id لـ Single ($29)
├── ls_unlimited_variant TEXT             -- variant_id لـ Unlimited ($79)
│
├── current_version     TEXT  NOT NULL    -- الإصدار الحالي (e.g. "1.2.0")
├── contract_version    TEXT              -- إصدار الـ theme_contract المُعتمد
├── domain              TEXT              -- نطاق القالب (e.g. "fashion")
├── cluster             TEXT              -- cluster المنظومة
├── woocommerce_enabled BOOL  DEFAULT FALSE
├── cod_enabled         BOOL  DEFAULT FALSE
│
├── [Provenance Fields]
├── build_id            TEXT              -- من حدث THEME_APPROVED
├── approved_event_id   TEXT  NOT NULL    -- event_id لحدث الموافقة
├── launch_idempotency_key TEXT           -- مفتاح الـ idempotency للإطلاق
│
├── [Version Tracking]
├── last_updated_at     TIMESTAMPTZ
├── last_update_event_id TEXT
├── last_update_idempotency_key TEXT
│
├── [Timestamps]
├── created_at          TIMESTAMPTZ DEFAULT NOW()
└── updated_at          TIMESTAMPTZ DEFAULT NOW()
```

**Validation Rules**:
- `theme_slug`: lowercase، a-z، 0-9، hyphens فقط
- `current_version`: SemVer format (MAJOR.MINOR.PATCH)
- `wp_post_id`: لا يُدرج في أي حدث وارد أو صادر
- `ls_single_variant` السعر ثابت = $29 (لا يُعدَّل بعد الإنشاء)
- `ls_unlimited_variant` السعر ثابت = $79

**State Transitions**:
```
[غير موجود] → [exists=true, version=X.Y.Z] → [updated: version=X.Y.Z+1]
```

---

### 2. InconsistentState (inconsistent_states)

تسجيل حالات التعارض بين WordPress و Lemon Squeezy.

```
InconsistentState
├── id              SERIAL  PK
├── theme_slug      TEXT    NOT NULL    -- FK إلى theme_registry (nullable)
├── error_code      TEXT    NOT NULL    -- دائماً PLT_303
├── wp_state        JSONB               -- حالة WordPress وقت الخطأ
├── ls_state        JSONB               -- حالة Lemon Squeezy وقت الخطأ
├── context         JSONB               -- سياق إضافي (node_name, idempotency_key)
├── notified_at     TIMESTAMPTZ         -- وقت إشعار صاحب المشروع
├── resolved_at     TIMESTAMPTZ  NULL   -- NULL = غير محلول
└── created_at      TIMESTAMPTZ  DEFAULT NOW()
```

**الحالة الحرجة**: إذا `resolved_at IS NULL` → يوقف كل workflow جديد للقالب.

---

### 3. ExecutionLog (execution_log)

يضمن idempotency على مستوى كل node.

```
ExecutionLog
├── idempotency_key     TEXT  PK    -- "launch:theme_slug:version" أو "update:..."
├── node_name           TEXT        -- اسم الـ LangGraph node
├── status              TEXT        -- "started" | "completed" | "failed"
├── last_completed_node TEXT        -- لاستئناف الـ workflow
├── result_snapshot     JSONB       -- snapshot من state عند الاكتمال
├── started_at          TIMESTAMPTZ DEFAULT NOW()
└── completed_at        TIMESTAMPTZ
```

**منطق الـ Idempotency Guard**:
```
إن (idempotency_key, node_name, status="completed") موجود → تجاوز التنفيذ
إلا → سجّل "started" → نفّذ → سجّل "completed"
```

---

### 4. VipRegistry (vip_registry)

سجل VIP Bundle — منتج Lemon Squeezy مستقل.

```
VipRegistry
├── id               SERIAL  PK
├── ls_product_id    TEXT  UNIQUE  -- معرّف منتج VIP في Lemon Squeezy
├── ls_variant_id    TEXT          -- variant_id لـ VIP Lifetime ($299)
├── theme_slugs      TEXT[]        -- قائمة القوالب المدرجة في الباقة
├── last_updated_at  TIMESTAMPTZ   DEFAULT NOW()
└── created_at       TIMESTAMPTZ   DEFAULT NOW()
```

**القاعدة**: `theme_slugs` يُحدَّث في `VIP_CATALOG_UPDATER` قبل `NEW_PRODUCT_LIVE`.

---

### 5. NotificationLog (notification_log)

لمنع إرسال إيميل التحديث أكثر من مرة لنفس المشتري.

```
NotificationLog
├── id               SERIAL  PK
├── buyer_email      TEXT  NOT NULL
├── theme_slug       TEXT  NOT NULL
├── version          TEXT  NOT NULL
├── sent_at          TIMESTAMPTZ  DEFAULT NOW()
└── UNIQUE(buyer_email, theme_slug, version)
```

---

## State Objects (LangGraph TypedDict)

### LaunchState

```python
class LaunchState(TypedDict):
    # Input
    theme_slug: str
    version: str
    theme_contract: dict
    package_path: str
    approved_event_id: str
    schema_version: str

    # Derived
    idempotency_key: str
    parsed: dict                   # من CONTRACT_PARSER
    collected_assets: dict         # من ASSET_WAITER (screenshot, etc.)

    # Lemon Squeezy
    ls_product_id: str
    ls_single_variant_id: str
    ls_unlimited_variant_id: str

    # WordPress
    wp_post_id: int                # من REGISTRY_RECORDER فقط
    wp_post_url: str

    # Review
    draft_page_content: dict       # من PAGE_WRITER
    page_blocks: str               # من PAGE_RENDERER (Gutenberg markup)
    review_decision: ReviewDecision
    revision_count: int
    review_notes: str

    # Control
    status: PlatformStatus
    error_code: str
    error_message: str
    revision_cycles: int
```

### UpdateState

```python
class UpdateState(TypedDict):
    # Input
    theme_slug: str
    new_version: str
    package_path: str
    changelog: dict
    event_id: str

    # From Registry
    idempotency_key: str
    ls_product_id: str
    wp_post_id: int
    wp_post_url: str
    previous_version: str

    # Processing
    eligible_buyers: list[dict]

    # Control
    status: PlatformStatus
    error_code: str
```

---

## Event Envelope (shared across all agents)

```json
{
  "event_id": "uuid-v4",
  "event_type": "NEW_PRODUCT_LIVE",
  "schema_version": "1.0",
  "occurred_at": "2026-03-22T10:00:00Z",
  "correlation_id": "uuid-v4",
  "data": { ... }
}
```

**القاعدة**: `wp_post_id` غائب من كل event.data — وارداً وصادراً.

---

## Relationships

```
theme_registry ──< inconsistent_states (theme_slug → theme_slug)
theme_registry ──< notification_log    (theme_slug → theme_slug)
execution_log ─── (idempotency_key مستقل — لا FK صريح)
vip_registry ─── (theme_slugs[] يحتوي theme_slug من theme_registry)
```

---

**Version**: 1.0.0 | **Date**: 2026-03-22

# Implementation Plan: Platform Agent — وكيل المنصة

**Branch**: `platform-agent-v1` | **Date**: 2026-03-22 | **Spec**: `agents/platform/docs/spec.md`
**Input**: `agents/platform/docs/spec.md` v3 (834 lines) + `constitution.md` v1.1.0
**Constitution**: `.specify/memory/constitution.md` v1.1.0

---

## Summary

وكيل المنصة هو حلقة الوصل بين منظومة نافع والأنظمة الخارجية (WordPress + Lemon Squeezy). يستقبل أحداث `THEME_APPROVED` و`THEME_UPDATED` من Redis Stream، يُنفّذ workflows متعددة الخطوات بنمط Saga، ويُطلق أحداث `NEW_PRODUCT_LIVE` و`THEME_UPDATED_LIVE` عند الاكتمال. يتعامل مع Webhooks واردة من Lemon Squeezy ويحوّلها إلى أحداث `NEW_SALE` و`LICENSE_ISSUED` على Redis.

---

## Technical Context

**Language/Version**: Python 3.12
**Framework**: LangGraph 0.2+ (StateGraph) + FastAPI 0.110+
**Primary Dependencies**:
- `langgraph` — Workflow graph engine
- `fastapi` + `uvicorn` — HTTP layer للـ webhooks والـ review API
- `psycopg2-binary` — PostgreSQL client
- `redis[hiredis]` — Redis Streams + Pub/Sub
- `httpx` — HTTP client لاستدعاء WordPress REST API + Lemon Squeezy API
- `resend` — إرسال الإيميلات
- `python-dotenv` — تحميل `.env`
- `pydantic` v2 — Validation للأحداث والـ state

**Storage**:
- PostgreSQL 15 — `theme_registry`, `vip_registry`, `inconsistent_states`, `execution_log`, `notification_log`
- Redis 7 — Streams (أحداث حرجة) + Pub/Sub (إشعارات)

**Testing**: pytest + pytest-asyncio + respx (mock httpx)
**Target Platform**: Linux server (Docker container)
**Project Type**: Event-driven microservice / LangGraph agent

**Performance Goals**:
- Webhook response: < 200ms p95
- Launch workflow: < 30 ثانية (بعد الموافقة)
- WordPress API: ≤ 60 req/min (مقيّد بـ Rate limiter)

**Constraints**:
- HTTPS فقط لكل استدعاءات خارجية
- `wp_post_id` من PostgreSQL فقط — لا من الأحداث أبداً
- كل node يحمل `@idempotency_guard`
- `INCONSISTENT_STATE` → يوقف كل workflow جديد حتى التدخل البشري

**Scale/Scope**: يخدم منصة نافع — متوسط ~10 قوالب/شهر، ~1000 مبيعة/شهر

---

## Constitution Check

*GATE: يجب اجتيازه قبل Phase 0. مُعاد التحقق بعد Phase 1.*

| المبدأ | الحالة | التحقق |
|--------|--------|--------|
| I. Human-First Approval | ✅ PASS | `THEME_APPROVED` + `HUMAN_REVIEW_GATE` مطلوبان في كل launch |
| II. Registry as Single Source of Truth | ✅ PASS | `wp_post_id` يُجلب من `ProductRegistry.get()` فقط |
| III. Idempotency Everywhere | ✅ PASS | `@idempotency_guard` على كل node، `idempotency_key` من السياق التجاري |
| IV. Saga — Best-Effort Consistency | ✅ PASS | Compensating actions + `INCONSISTENT_STATE` عند فشل rollback |
| V. Price Immutability | ✅ PASS | الأسعار تُحدد مرة واحدة في `LICENSE_CONFIGURATOR` ($29/$79) |
| VI. API Credential Isolation | ✅ PASS | كل credentials في `.env` فقط، HTTPS مُطبَّق برمجياً |
| VII. Webhook Integrity | ✅ PASS | HMAC-SHA256 verification أول خطوة دائماً |
| VIII. Failure Transparency | ✅ PASS | كل node يرفع `PlatformError` بكود محدد |
| IX. VIP Bundle | ✅ PASS | VIP منتج مستقل بـ `ls_product_id` خاص |
| X. Changelog Contract | ✅ PASS | `CHANGELOG_VALIDATOR` يرفض `PLT_803` عند فشل التحقق |

**نتيجة**: جميع البوابات تجتاز — لا انتهاكات.

---

## Project Structure

### Documentation

```text
agents/platform/platform-agent/.specify/memory/
├── constitution.md          # v1.1.0 ✅ مكتمل
├── plan.md                  # هذا الملف ✅
├── data-model.md            # Phase 1 output
└── contracts/               # Phase 1 output
    ├── events.md            # Event Envelope contracts
    └── api.md               # FastAPI endpoints contract

agents/platform/platform-agent/docs/tasks/
├── tasks.md                 # Master task list ✅ مكتمل
├── phase1_setup.md          # T001–T005 ✅ مكتمل
├── phase2_foundation.md     # T010–T035 ✅ مكتمل
├── phase3_launch_workflow.md # T040–T054 ✅ مكتمل
├── phase4_update_workflow.md # T055–T065 ✅ مكتمل
└── phase5_commerce_consumer.md # T070–T085 ✅ مكتمل
```

### Source Code

```text
agents/platform/platform-agent/
├── agent.py                     # build_launch_graph() + build_update_graph()
├── state.py                     # LaunchState, UpdateState, PlatformStatus, ReviewDecision
├── pyproject.toml               # Dependencies
├── Dockerfile                   # Container definition
├── .env.example                 # Template لبيانات الاعتماد
│
├── db/
│   ├── registry.py              # ProductRegistry — Single Source of Truth
│   ├── idempotency.py           # @idempotency_guard decorator
│   └── migrations/
│       └── 001_initial.sql      # theme_registry, vip_registry, inconsistent_states, execution_log
│
├── services/
│   ├── wp_client.py             # WordPressClient (HTTPS only, Editor user)
│   ├── ls_client.py             # LemonSqueezyClient (Products + Variants + Files)
│   ├── redis_bus.py             # RedisBus (Streams + Pub/Sub) + build_event()
│   └── resend_client.py         # ResendClient (إيميلات الإشعارات)
│
├── nodes/
│   ├── launch/                  # 13 node لـ Launch Workflow
│   │   ├── launch_entry.py
│   │   ├── inconsistency_check.py
│   │   ├── contract_parser.py
│   │   ├── asset_waiter.py
│   │   ├── product_creator.py
│   │   ├── license_configurator.py
│   │   ├── vip_catalog_updater.py
│   │   ├── page_writer.py
│   │   ├── page_renderer.py
│   │   ├── human_review_gate.py
│   │   ├── saga_publisher.py
│   │   ├── registry_recorder.py
│   │   └── launch_announcer.py
│   └── update/                  # 9 node لـ Update Workflow
│       ├── update_entry.py
│       ├── changelog_validator.py
│       ├── registry_loader.py
│       ├── wp_content_updater.py
│       ├── ls_file_updater.py
│       ├── eligibility_filter.py
│       ├── notification_sender.py
│       ├── version_recorder.py
│       └── update_announcer.py
│
├── commerce/
│   └── webhook_handler.py       # CommerceEventConsumer + HMAC verification
│
├── listeners/
│   ├── launch_listener.py       # يستمع على theme-events لـ THEME_APPROVED
│   └── update_listener.py       # يستمع على theme-events لـ THEME_UPDATED
│
├── api/
│   ├── main.py                  # FastAPI: /webhooks/lemonsqueezy + /health + /review + /assets
│   └── background.py            # Timeout watchdog (كل 5 دقائق)
│
└── templates/
    ├── update_notification.html
    ├── launch_confirmation.html
    └── inconsistency_alert.html
```

**Structure Decision**: Single-agent service pattern — كل شيء في مجلد واحد مع فصل واضح بين layers (db، services، nodes، api). لا frontend.

---

## Workflow Architecture

### Workflow 1: Launch (THEME_APPROVED → NEW_PRODUCT_LIVE)

```
Redis Stream: theme-events
    └── THEME_APPROVED
        └── LaunchListener
            └── build_launch_graph()
                ├── LAUNCH_ENTRY              → validates event + creates idempotency_key
                ├── INCONSISTENCY_CHECK       → blocks if unresolved INCONSISTENT_STATE
                ├── CONTRACT_PARSER           → extracts theme_contract fields
                ├── ASSET_WAITER              → suspends if assets not ready (max 8h)
                ├── PRODUCT_CREATOR           → creates LS product (draft)
                ├── LICENSE_CONFIGURATOR      → sets Single=$29, Unlimited=$79
                ├── VIP_CATALOG_UPDATER       → adds theme_slug to vip_registry
                ├── PAGE_WRITER               → generates structured page JSON
                ├── PAGE_RENDERER             → converts to Gutenberg blocks
                ├── HUMAN_REVIEW_GATE ⏸       → waits for owner decision (max 48h)
                │   ├── approved → SAGA_PUBLISHER
                │   ├── needs_revision (< 3) → PAGE_WRITER
                │   ├── needs_revision (= 3) → LAUNCH_HOLD
                │   └── rejected → LAUNCH_CANCEL
                ├── SAGA_PUBLISHER            → WP publish + LS activate (Saga)
                ├── REGISTRY_RECORDER         → saves ThemeRecord with full Provenance
                └── LAUNCH_ANNOUNCER          → publishes NEW_PRODUCT_LIVE + email
```

### Workflow 2: Update (THEME_UPDATED → THEME_UPDATED_LIVE)

```
Redis Stream: theme-events
    └── THEME_UPDATED
        └── UpdateListener
            └── build_update_graph()
                ├── UPDATE_ENTRY              → validates + idempotency_key
                ├── CHANGELOG_VALIDATOR       → enforces Changelog Contract (X)
                ├── REGISTRY_LOADER           → fetches wp_post_id from DB
                ├── WP_CONTENT_UPDATER        → updates WordPress post
                ├── LS_FILE_UPDATER           → updates LS product file (no price change)
                ├── ELIGIBILITY_FILTER        → determines who gets update email
                ├── NOTIFICATION_SENDER       → sends emails via Resend
                ├── VERSION_RECORDER          → updates theme_registry version
                └── UPDATE_ANNOUNCER          → publishes THEME_UPDATED_LIVE
```

### Workflow 3: Commerce (Lemon Squeezy Webhook → Redis Events)

```
POST /webhooks/lemonsqueezy
    └── CommerceEventConsumer.handle_webhook()
        ├── _verify_signature()        → HMAC-SHA256 (PLT_1001 on failure)
        └── dispatch by event_name:
            ├── order_created   → _handle_new_sale()    → NEW_SALE on sales-events
            └── license_created → _handle_license_issued() → LICENSE_ISSUED on sales-events
```

---

## Error Code Registry

| الكود | الـ Node | السبب |
|-------|---------|-------|
| PLT_101 | LAUNCH_ENTRY | القالب موجود بالفعل في Registry |
| PLT_201 | PRODUCT_CREATOR | فشل إنشاء منتج Lemon Squeezy |
| PLT_301 | SAGA_PUBLISHER | فشل إنشاء WordPress post |
| PLT_303 | INCONSISTENCY_CHECK / SAGA | تسجيل INCONSISTENT_STATE |
| PLT_401 | REGISTRY_RECORDER | فشل حفظ السجل في PostgreSQL |
| PLT_501 | BACKGROUND | انتهاء مهلة HUMAN_REVIEW (48h) |
| PLT_601 | PAGE_WRITER | فشل توليد محتوى الصفحة |
| PLT_602 | PAGE_RENDERER | فشل Gutenberg validation |
| PLT_701 | REGISTRY_LOADER | القالب غير موجود في Registry |
| PLT_702 | UPDATE_ENTRY | الإصدار مكرر |
| PLT_703 | WP_CONTENT_UPDATER | فشل تحديث WordPress |
| PLT_704 | LS_FILE_UPDATER | فشل تحديث ملف Lemon Squeezy |
| PLT_803 | CHANGELOG_VALIDATOR | Changelog غير صالح |
| PLT_804 | LAUNCH_ENTRY | `schema_version` غير مدعوم |
| PLT_901 | NOTIFICATION_SENDER | فشل كلي في إرسال الإيميلات |
| PLT_902 | NOTIFICATION_SENDER | فشل جزئي (يكمل) |
| PLT_1001 | webhook_handler | HMAC verification فشل |

---

## Saga Failure Matrix

| السيناريو | الـ Compensating Action | عند فشل الـ Rollback |
|----------|------------------------|---------------------|
| WP نجح + LS فشل | `wp_client.delete_theme_product(wp_post_id)` | `registry.record_inconsistent_state()` + PLT_303 |
| LS نجح + WP فشل | `ls_client.deactivate_product(ls_product_id)` | `registry.record_inconsistent_state()` + PLT_303 |

---

## Complexity Tracking

لا انتهاكات — النمط الموجود (Saga + Idempotency + Registry) مبرر بوجود نظامين خارجيين مستقلين لا يمكن إدراجهما في transaction واحدة (المبدأ IV).

---

## Implementation Phases

| المرحلة | المحتوى | المهام | الحالة |
|---------|---------|--------|--------|
| Phase 1 | Setup (pyproject + .env + Docker) | T001–T005 | ⬜ pending |
| Phase 2 | Foundation (DB + Services) | T010–T035 | ⬜ pending |
| Phase 3 | Launch Workflow | T040–T054 | ⬜ pending |
| Phase 4 | Update Workflow | T055–T065 | ⬜ pending |
| Phase 5 | Commerce Consumer + FastAPI | T070–T085 | ⬜ pending |

**ترتيب التنفيذ**: Phase 1 → Phase 2 → (Phase 3 + Phase 4 معاً) → Phase 5

---

**Version**: 1.0.0 | **Date**: 2026-03-22 | **Author**: spec-kit via Claude

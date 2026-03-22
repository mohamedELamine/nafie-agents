---
description: "Phase 2: Foundation — Core Infrastructure"
---

# Phase 2: Foundation

**Goal**: البنية التحتية الأساسية التي تعتمد عليها كل الـ workflows
**Prerequisites**: Phase 1 مكتملة
**⚠️ CRITICAL**: لا workflow يمكن أن يعمل قبل اكتمال هذه المرحلة

---

## § A — Database Layer (T010–T018)

**الملف الأساسي**: `agents/platform/platform-agent/db/registry.py`
**Migration**: `agents/platform/platform-agent/db/migrations/001_initial.sql`

- [ ] T010 تنفيذ `ProductRegistry.exists(theme_slug)` → bool
  - استعلام: `SELECT 1 FROM theme_registry WHERE theme_slug = %s`

- [ ] T011 تنفيذ `ProductRegistry.get(theme_slug)` → Optional[Dict]
  - يُعيد السجل كاملاً بما فيه `wp_post_id`
  - **قاعدة حرجة**: `wp_post_id` يأتي من هنا فقط

- [ ] T012 تنفيذ `ProductRegistry.save(record)` → None
  - يحفظ ThemeRecord مع Provenance كامل
  - يرفع `PLT_401` عند الفشل

- [ ] T013 تنفيذ `ProductRegistry.update_version(theme_slug, new_version, event_id, idempotency_key)` → None
  - يحدث: `current_version`, `last_updated_at`, `last_update_event_id`, `last_update_idempotency_key`

- [ ] T014 تنفيذ `ProductRegistry.has_unresolved_inconsistency(theme_slug)` → bool
  - استعلام: `SELECT 1 FROM inconsistent_states WHERE theme_slug = %s AND resolved_at IS NULL`

- [ ] T015 تنفيذ `ProductRegistry.record_inconsistent_state(theme_slug, wp_state, ls_state)` → None
  - يُدرج في `inconsistent_states`
  - يُرسل تنبيهاً فورياً لصاحب المشروع

- [ ] T016 تنفيذ `ProductRegistry.get_all_published()` → List[Dict]
- [ ] T017 تنفيذ `ProductRegistry.get_launch_date(theme_slug)` → Optional[datetime]
- [ ] T018 تنفيذ `ProductRegistry.count_published()` → int

---

## § B — Idempotency Guard (T019)

**الملف**: `agents/platform/platform-agent/db/idempotency.py` (ملف جديد)

- [ ] T019 [P] تنفيذ `idempotency_guard(node_name)` decorator
  - يتحقق من `execution_log` قبل تنفيذ الـ node
  - إن `status == "completed"` → يتجاوز التنفيذ ويعيد state
  - يُسجّل البدء والاكتمال في `execution_log`
  - المرجع: spec.md § ٥

---

## § C — WordPress Client (T020–T023)

**الملف**: `agents/platform/platform-agent/services/wp_client.py`

- [ ] T020 تنفيذ `WordPressClient.create_theme_product(post_data)` → Dict
  - POST `/wp-json/wp/v2/ar_theme_product`
  - يُعيد `{"id": int, "link": str}`
  - يرفع exception بـ `PLT_301` عند الفشل

- [ ] T021 تنفيذ `WordPressClient.update_theme_product(wp_post_id, post_data)` → Dict
  - PUT `/wp-json/wp/v2/ar_theme_product/{id}`
  - يرفع exception بـ `PLT_703` عند الفشل

- [ ] T022 تنفيذ `WordPressClient.delete_theme_product(wp_post_id)` → bool
  - DELETE `/wp-json/wp/v2/ar_theme_product/{id}`
  - للـ rollback في Saga — يعيد False (لا يرفع) عند الفشل

- [ ] T023 [P] تنفيذ `WordPressClient.upload_media(file_path, alt_text)` → Dict
  - POST `/wp-json/wp/v2/media`
  - يتحقق: WebP فقط، حد أقصى 2MB
  - يُعيد `{"id": int, "source_url": str}`

---

## § D — Lemon Squeezy Client (T024–T030)

**الملف**: `agents/platform/platform-agent/services/ls_client.py`

- [ ] T024 تنفيذ `LemonSqueezyClient.create_product(name_ar, theme_slug)` → Dict
  - ينشئ منتجاً بـ status=draft
  - ينشئ variant واحد لـ Single ($29) وآخر لـ Unlimited ($79)
  - يُعيد `{"product_id": str, "single_variant_id": str, "unlimited_variant_id": str}`
  - يرفع `PLT_201` عند الفشل

- [ ] T025 تنفيذ `LemonSqueezyClient.activate_product(ls_product_id)` → bool
  - PATCH status إلى published
  - يُستدعى من SAGA_PUBLISHER فقط

- [ ] T026 تنفيذ `LemonSqueezyClient.deactivate_product(ls_product_id)` → bool
  - PATCH status إلى draft
  - Compensating action — يعيد False (لا يرفع) عند الفشل

- [ ] T027 تنفيذ `LemonSqueezyClient.update_product_file(ls_product_id, zip_path)` → bool
  - يُحدّث ملف القالب على Lemon Squeezy
  - يرفع `PLT_704` عند الفشل

- [ ] T028 تنفيذ `LemonSqueezyClient.get_active_licenses(ls_product_id)` → List[Dict]
  - يجلب المشترين الذين `license_status == "active"` و `updates_entitlement == True`

- [ ] T029 تنفيذ `LemonSqueezyClient.get_vip_product()` → Optional[Dict]
- [ ] T030 تنفيذ `LemonSqueezyClient.add_theme_to_vip(vip_product_id, theme_slug)` → bool

---

## § E — Redis Bus (T031–T033)

**الملف**: `agents/platform/platform-agent/services/redis_bus.py`

- [ ] T031 تنفيذ `RedisBus.publish(channel, event)` → None
  - `redis.publish(channel, json.dumps(event))`

- [ ] T032 تنفيذ `RedisBus.publish_stream(stream, event)` → str
  - `redis.xadd(stream, {"data": json.dumps(event)})`
  - للأحداث الحرجة: `product-events`, `sales-events`

- [ ] T033 التحقق من `build_event()` — يجب أن يُنتج Event Envelope كامل حسب spec.md § ١٧

---

## § F — Resend Client (T034–T035)

**الملف**: `agents/platform/platform-agent/services/resend_client.py`

- [ ] T034 [P] تثبيت مكتبة `resend` وتهيئة الـ API key من `.env`
- [ ] T035 [P] إنشاء templates HTML للإيميلات في `agents/platform/platform-agent/templates/`
  - `update_notification.html`
  - `launch_confirmation.html`
  - `inconsistency_alert.html`

**Checkpoint ✅**: كل الـ services تُنشأ بدون أخطاء و `.env` محمّل

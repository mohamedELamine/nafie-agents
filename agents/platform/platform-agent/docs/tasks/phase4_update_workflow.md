---
description: "Phase 4: Product Update Workflow (Workflow 2)"
---

# Phase 4: Product Update Workflow

**Goal**: تنفيذ Workflow تحديث قالب موجود
**Prerequisites**: Phase 2 مكتملة
**المرجع**: `agents/platform/docs/spec.md § ٧`
**المُشغِّل**: حدث `THEME_UPDATED` على Redis Stream `theme-events`

---

## خريطة الـ Workflow

```
UPDATE_ENTRY → CHANGELOG_VALIDATOR → REGISTRY_LOADER
    → WP_CONTENT_UPDATER → LS_FILE_UPDATER
    → ELIGIBILITY_FILTER → NOTIFICATION_SENDER
    → VERSION_RECORDER → UPDATE_ANNOUNCER → END
```

---

## Tasks (T055–T069)

### T055 — UPDATE_ENTRY
**الملف**: `nodes/update/update_entry.py`

- استخرج: `theme_slug`, `new_version`, `package_path`, `changelog`, `event_id`
- أنشئ `idempotency_key = f"update:{theme_slug}:{new_version}"`
- تحقق من `schema_version`
- تحقق: إن `new_version == current_version` في Registry → `PLT_702`

---

### T056 — CHANGELOG_VALIDATOR
**الملف**: `nodes/update/changelog_validator.py`

```python
def validate_changelog(changelog: dict) -> bool:
```
- يتحقق من:
  - `summary_ar` موجود وغير فارغ
  - `items_ar` قائمة غير فارغة
  - `type` ∈ {"patch", "minor", "major"}
  - `is_security` bool
- يرفع `PLT_803` عند الفشل

---

### T057 — REGISTRY_LOADER
**الملف**: `nodes/update/registry_loader.py`

- `registry.get(theme_slug)` — **wp_post_id يأتي من هنا فقط**
- إن غير موجود → `PLT_701`
- احفظ في state: `ls_product_id`, `ls_single_variant`, `ls_unlimited_variant`, `wp_post_id`, `wp_post_url`, `previous_version`

---

### T058 — WP_CONTENT_UPDATER
**الملف**: `nodes/update/wp_content_updater.py`

- `wp_client.update_theme_product(wp_post_id, updated_content)`
- wp_post_id جاء من REGISTRY_LOADER — **لا من الحدث الوارد**
- يرفع `PLT_703` عند الفشل

---

### T059 — LS_FILE_UPDATER
**الملف**: `nodes/update/ls_file_updater.py`

- `ls_client.update_product_file(ls_product_id, package_path)`
- يرفع `PLT_704` عند الفشل
- **السعر لا يُمس** — فقط تحديث الملف

---

### T060 — ELIGIBILITY_FILTER
**الملف**: `nodes/update/eligibility_filter.py`

```python
def eligible_for_update_email(buyer, changelog, theme_slug, new_version) -> bool:
```
- Idempotency: إن `notification_log.exists(email, theme_slug, new_version)` → False
- التحديثات الأمنية (`is_security == True`) تتجاوز `email_opt_in`
- الشروط العادية: `license_status == "active"` + `updates_entitlement == True` + `email_opt_in == True`
- احفظ `eligible_buyers` في state

---

### T061 — NOTIFICATION_SENDER
**الملف**: `nodes/update/notification_sender.py`

- أرسل إيميل لكل `buyer` في `eligible_buyers`
- Template: `templates/update_notification.html`
- سجّل في `notification_log` لمنع التكرار
- عند فشل كلي: `PLT_901`
- عند فشل جزئي: `PLT_902` (يكمل ولا يتوقف)

---

### T062 — VERSION_RECORDER
**الملف**: `nodes/update/version_recorder.py`

- `registry.update_version(theme_slug, new_version, event_id, idempotency_key)`
- يُحدّث: `current_version`, `last_updated_at`, `last_update_event_id`, `last_update_idempotency_key`

---

### T063 — UPDATE_ANNOUNCER
**الملف**: `nodes/update/update_announcer.py`

- أطلق `THEME_UPDATED_LIVE` على Redis Stream `product-events`:
  ```json
  {
    "event_type": "THEME_UPDATED_LIVE",
    "schema_version": "1.0",
    "data": {
      "theme_slug": "...",
      "new_version": "...",
      "is_security": false,
      "buyers_notified": 42
    }
  }
  ```

---

### T064 — بناء Update Graph
**الملف**: `agent.py` → `build_update_graph()`

- أضف كل node بترتيب الخريطة
- Routing: بعد `CHANGELOG_VALIDATOR` إن فشل → END

---

### T065 — Redis Stream Listener للتحديثات
**الملف**: `listeners/update_listener.py` (ملف جديد)

- يستمع على `theme-events` Stream لـ `THEME_UPDATED`
- يُشغّل `build_update_graph()`

**Checkpoint ✅**: إرسال `THEME_UPDATED` يُنتج `THEME_UPDATED_LIVE` + إيميلات للمشترين

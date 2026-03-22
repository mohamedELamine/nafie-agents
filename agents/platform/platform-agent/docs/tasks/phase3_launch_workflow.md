---
description: "Phase 3: Product Launch Workflow (Workflow 1)"
---

# Phase 3: Product Launch Workflow

**Goal**: تنفيذ كامل لـ Workflow إطلاق قالب جديد
**Prerequisites**: Phase 2 مكتملة بالكامل
**المرجع**: `agents/platform/docs/spec.md § ٦`
**المُشغِّل**: حدث `THEME_APPROVED` على Redis Stream `theme-events`

---

## خريطة الـ Workflow

```
LAUNCH_ENTRY → INCONSISTENCY_CHECK → CONTRACT_PARSER
    → ASSET_WAITER → PRODUCT_CREATOR → LICENSE_CONFIGURATOR
    → VIP_CATALOG_UPDATER → PAGE_WRITER → PAGE_RENDERER
    → HUMAN_REVIEW_GATE → SAGA_PUBLISHER → REGISTRY_RECORDER
    → LAUNCH_ANNOUNCER → END
```

---

## § A — Nodes (T040–T053)

### T040 — LAUNCH_ENTRY
**الملف**: `nodes/launch/launch_entry.py`

```python
@idempotency_guard("LAUNCH_ENTRY")
def launch_entry_node(state):
```
- استخرج: `theme_slug`, `version`, `theme_contract`, `package_path`, `approved_event_id`
- أنشئ `idempotency_key = f"launch:{theme_slug}:{version}"`
- إن `registry.exists(theme_slug)` → `error_code = PLT_101`, `status = FAILED`
- تحقق من `schema_version` → إن غير مدعوم: `PLT_804`

---

### T041 — INCONSISTENCY_CHECK
**الملف**: `nodes/launch/inconsistency_check.py`

```python
@idempotency_guard("INCONSISTENCY_CHECK")
def inconsistency_check_node(state):
```
- إن `registry.has_unresolved_inconsistency(theme_slug)` → `PLT_303`, `status = INCONSISTENT_EXTERNAL_STATE`
- أرسل تنبيهاً فورياً لصاحب المشروع

---

### T042 — CONTRACT_PARSER
**الملف**: `nodes/launch/contract_parser.py`

```python
@idempotency_guard("CONTRACT_PARSER")
def contract_parser_node(state):
```
- فك تشفير `theme_contract` واستخرج: `theme_name_ar`, `domain`, `cluster`, `build_version`
- استدعِ `get_required_sections(theme_contract)` لتحديد أقسام الصفحة
- احفظ في `state["parsed"]`

---

### T043 — ASSET_WAITER
**الملف**: `nodes/launch/asset_waiter.py`

```python
@idempotency_guard("ASSET_WAITER")
def asset_waiter_node(state):
```
- إن الأصول موجودة في `state["collected_assets"]` → تابع
- إن غير موجودة:
  - `status = WAITING_ASSETS`
  - سجّل checkpoint في Redis: `workflow:{idempotency_key}` مع `last_node = "ASSET_WAITER"`
  - أرسل `END` — سيستأنف عند استلام `THEME_ASSETS_READY`
- **قاعدة**: لا نشر دون `screenshot` حتى لو قرر صاحب المشروع بالمتابعة
- **Asset Timeout Policy** (spec.md § ١٣):
  - بعد 4 ساعات: أشعر صاحب المشروع بالخيارات
  - بعد 8 ساعات: إلغاء تلقائي

---

### T044 — PRODUCT_CREATOR
**الملف**: `nodes/launch/product_creator.py`

```python
@idempotency_guard("PRODUCT_CREATOR")
def product_creator_node(state):
```
- استدعِ `ls_client.create_product(theme_name_ar, theme_slug)`
- احفظ `ls_product_id`, `ls_variants` في state
- يرفع `PLT_201` عند الفشل

---

### T045 — LICENSE_CONFIGURATOR
**الملف**: `nodes/launch/license_configurator.py`

```python
@idempotency_guard("LICENSE_CONFIGURATOR")
def license_configurator_node(state):
```
- أنشئ variants على Lemon Squeezy: Single ($29) + Unlimited ($79)
- **قاعدة**: السعر لا يُمس بعد هذه النقطة أبداً

---

### T046 — VIP_CATALOG_UPDATER
**الملف**: `nodes/launch/vip_catalog_updater.py`

```python
@idempotency_guard("VIP_CATALOG_UPDATER")
def vip_catalog_updater_node(state):
```
- جلب VIP Bundle: `ls_client.get_vip_product()`
- إضافة `theme_slug` للـ `vip_registry.theme_slugs`
- **VIP منتج مستقل** — لا variant داخل المنتج الجديد

---

### T047 — PAGE_WRITER
**الملف**: `nodes/launch/page_writer.py`

```python
@idempotency_guard("PAGE_WRITER")
def page_writer_node(state):
```
- أنشئ JSON منظم لصفحة المنتج بالأقسام المطلوبة من `get_required_sections()`
- الأقسام الإلزامية: hero, features, target_audience, quality_section, pricing_section, faq, cta
- الأقسام الشرطية: woocommerce_features (إن `woocommerce_enabled`), cod_features (إن `cod_enabled`)
- أدخل الأسعار من `ls_variants`
- احفظ في `state["draft_page_content"]`

---

### T048 — PAGE_RENDERER
**الملف**: `nodes/launch/page_renderer.py`

```python
@idempotency_guard("PAGE_RENDERER")
def page_renderer_node(state):
```
- حوّل JSON إلى Gutenberg block markup
- `validate_gutenberg_markup(rendered, required_sections)`
- إن validation فشل: `PLT_602`
- احفظ في `state["page_blocks"]`
- **ممنوع**: LLM-generated markup مباشرة دون renderer ثابت

---

### T049 — HUMAN_REVIEW_GATE
**الملف**: `nodes/launch/human_review_gate.py`

```python
def human_review_gate_node(state):
def route_after_review(state) -> str:
```
- أرسل صفحة المنتج لصاحب المشروع للمراجعة
- انتظر قرار: `approved_as_is`, `approved_with_edits`, `needs_revision_minor/major`, `rejected`
- `MAX_REVISION_CYCLES = 3`
- routing:
  - approved → PAGE_RENDERER (أو SAGA_PUBLISHER مباشرة)
  - needs_revision (< 3) → PAGE_WRITER مع ملاحظات
  - needs_revision (= 3) → LAUNCH_HOLD + إشعار
  - rejected → LAUNCH_CANCEL

---

### T050 — SAGA_PUBLISHER
**الملف**: `nodes/launch/saga_publisher.py`

```python
@idempotency_guard("SAGA_PUBLISHER")
def saga_publisher_node(state):
```
- **الخطوة 1**: `wp_client.create_theme_product(...)` → احفظ `wp_post_id`
- **الخطوة 2**: `ls_client.activate_product(ls_product_id)`
- **عند الفشل** (Compensating actions):
  - إن WP نجح وLS فشل → `wp_client.delete_theme_product(wp_post_id)`
  - إن الـ rollback فشل → `registry.record_inconsistent_state(...)` + `PLT_303`
- **لا ضمان ذرية حقيقية** — best-effort consistency

---

### T051 — REGISTRY_RECORDER
**الملف**: `nodes/launch/registry_recorder.py`

```python
@idempotency_guard("REGISTRY_RECORDER")
def registry_recorder_node(state):
```
- احفظ `ThemeRecord` مع Provenance كامل:
  - `contract_version`, `build_id`, `approved_event_id`, `launch_idempotency_key`
- `registry.save(record)` → يرفع `PLT_401` عند الفشل

---

### T052 — LAUNCH_ANNOUNCER
**الملف**: `nodes/launch/launch_announcer.py`

```python
@idempotency_guard("LAUNCH_ANNOUNCER")
def launch_announcer_node(state):
```
- أطلق `NEW_PRODUCT_LIVE` على Redis Stream `product-events`:
  ```json
  {
    "event_type": "NEW_PRODUCT_LIVE",
    "schema_version": "1.0",
    "data": {
      "theme_slug": "...",
      "theme_name_ar": "...",
      "wp_post_url": "...",
      "ls_product_id": "...",
      "pricing": {"single": 29, "unlimited": 79, "vip": 299},
      "final_score": 91
    }
  }
  ```
- أرسل تأكيد إطلاق لصاحب المشروع عبر Resend

---

## § B — LangGraph Assembly (T053)

### T053 — بناء Launch Graph
**الملف**: `agents/platform/platform-agent/agent.py`

```python
def build_launch_graph():
    graph = StateGraph(LaunchState)
    # أضف كل node
    # أضف edges مع routing
    # أضف conditional edges لـ HUMAN_REVIEW_GATE وASET_WAITER
```

**Routing Rules**:
- بعد `INCONSISTENCY_CHECK`: إن `status == INCONSISTENT_EXTERNAL_STATE` → END
- بعد `ASSET_WAITER`: إن `status == WAITING_ASSETS` → END
- بعد `HUMAN_REVIEW_GATE`: `route_after_review(state)`
- بعد `SAGA_PUBLISHER`: إن `status == INCONSISTENT_EXTERNAL_STATE` → END

---

## § C — Event Listener (T054)

### T054 — Redis Stream Listener
**الملف**: `agents/platform/platform-agent/listeners/launch_listener.py` (ملف جديد)

- يستمع على `theme-events` Stream لـ `THEME_APPROVED`
- يستمع على `asset-events` Stream لـ `THEME_ASSETS_READY` و `THEME_ASSETS_PARTIALLY_READY`
- عند استلام `THEME_ASSETS_READY`:
  - جلب checkpoint من Redis: `workflow:{idempotency_key}`
  - استئناف الـ graph من `ASSET_WAITER`

**Checkpoint ✅**: إرسال حدث `THEME_APPROVED` يُشغّل الـ workflow ويُنتج `NEW_PRODUCT_LIVE`

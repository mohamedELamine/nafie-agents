<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — إعادة هيكلة المبدأ السادس إلى مبدأين (VI + VII)
                       + تقوية المبدأ VIII (INCONSISTENT_STATE كحاجز صريح)
                       + تنظيف الصياغة لتتوافق مع معيار spec-kit

Modified principles:
  - VI. Security-First → انقسم إلى:
      VI.  API Credential Isolation (حماية البيانات الحساسة)
      VII. Webhook Integrity (أمان الـ webhooks مستقلاً)
  - VIII. Failure Transparency → أُضيف: INCONSISTENT_STATE يمنع كل workflow جديد

Templates updated:
  ✅ .specify/memory/constitution.md (هذا الملف)
  ✅ docs/tasks/tasks.md (القواعد المطلقة متوافقة)
  ✅ agents/platform/docs/spec.md v3 (المصدر)

Deferred TODOs:
  - WP_SITE_URL: يُحدَّد عند تأكيد الـ domain
-->

# Platform Agent Constitution — وكيل المنصة

## Core Principles

### I. Human-First Approval
وكيل المنصة لا يتخذ أي إجراء تشغيلي دون موافقة صريحة من صاحب المشروع.

MUST: كل إطلاق قالب يبدأ بحدث `THEME_APPROVED` — لا استثناء ولا مسار بديل.
MUST: صفحة المنتج لا تُنشر على WordPress قبل اجتياز `HUMAN_REVIEW_GATE`.
MUST: قرارات المراجعة البشرية تصل عبر API endpoint مصادق عليه — لا من الأحداث.
MUST NOT: لا يُستأنَف `INCONSISTENT_STATE` آلياً تحت أي ظرف.
RATIONALE: المنظومة تُنفّذ التشغيل — صاحب المشروع يُقرّر الاستراتيجية.

---

### II. Registry as Single Source of Truth
`theme_registry` في PostgreSQL هو المرجع الوحيد لحالة القوالب وبياناتها.

MUST: `wp_post_id` يُجلب من `theme_registry` فقط — في كل عملية بلا استثناء.
MUST NOT: لا يُدرج `wp_post_id` في أي حدث وارد أو صادر.
MUST: كل سجل يحمل Provenance كاملاً: `build_id`, `approved_event_id`, `launch_idempotency_key`.
MUST: أي تعارض بين Lemon Squeezy وRedis → Lemon Squeezy يفوز للبيانات المالية.
RATIONALE: منع تشعّب مصادر الحقيقة الذي يُفضي إلى حالات غير متسقة غير قابلة للتشخيص.

---

### III. Idempotency Everywhere
كل عملية في وكيل المنصة آمنة للتكرار — نفس المدخل ينتج نفس النتيجة دائماً.

MUST: كل node يحمل decorator `@idempotency_guard(node_name)`.
MUST: `idempotency_key` مُشتق من السياق التجاري: `event_type:theme_slug:version`.
MUST: الحدث المكرر يُتجاوز بصمت مع تسجيل `[SKIP]` في logs — لا خطأ.
MUST: كل حدث صادر يحمل `event_id` فريداً (uuid-v4) و`schema_version: "1.0"`.

---

### IV. Saga — Best-Effort Consistency
النشر عبر WordPress + Lemon Squeezy عملية Saga — لا ضمان ذرية حقيقية.

MUST: تنفيذ Compensating actions فور فشل أي خطوة.
MUST: إن فشل الـ rollback → تسجيل `INCONSISTENT_STATE` في `inconsistent_states` فوراً.
MUST: إشعار صاحب المشروع عند تسجيل `INCONSISTENT_STATE` — قبل أي إجراء آخر.
MUST NOT: لا ادعاء بضمان ذرية حقيقية في الكود أو الوثائق.
MUST NOT: لا workflow جديد لقالب عليه `INCONSISTENT_STATE` غير محلول.
RATIONALE: نظامان خارجيان مستقلان لا يمكن إدراجهما في transaction واحدة.

---

### V. Price Immutability
الأسعار عقد ملزم مع المشترين — لا تُعدَّل بعد النشر أبداً.

MUST: الأسعار تُحدَّد مرة واحدة في `LICENSE_CONFIGURATOR` فقط.
MUST NOT: لا node آخر يملك صلاحية تعديل الأسعار.
MUST NOT: لا إشارة تحليلية أو أمر خارجي يُعطي وكيل المنصة صلاحية تغيير السعر.
PRICING: single_site=$29 · unlimited=$79 · vip_lifetime=$299 (ثابتة في الكود).

---

### VI. API Credential Isolation
بيانات الاعتماد للأنظمة الخارجية محمية ومعزولة تماماً عن منطق الأعمال.

MUST: كل credentials في `.env` فقط — لا في الكود، لا في الـ logs، لا في الأحداث.
MUST: WordPress API يعمل عبر مستخدم Editor مخصص — لا Admin.
MUST: HTTPS فقط لكل استدعاءات WordPress REST API — رفض HTTP برمجياً.
MUST: Rate limiting على WordPress API: 60 طلب/دقيقة.
MUST: WordPress API مقيّد بـ `ar_theme_product` Custom Post Type فقط.

---

### VII. Webhook Integrity
كل Webhook وارد من Lemon Squeezy يُتحقق منه قبل أي معالجة.

MUST: التحقق من HMAC-SHA256 signature هو الخطوة الأولى دائماً — قبل parse.
MUST: فشل التحقق → رفض فوري بـ `PLT_1001` دون الاطلاع على المحتوى.
MUST NOT: لا معالجة لأي Webhook بدون signature صالح تحت أي ظرف.
RATIONALE: Webhook بدون تحقق يعرّض المنظومة لهجمات حقن أحداث مزيفة.

---

### VIII. Failure Transparency — الفشل الصامت ممنوع
كل خطأ معروف ومُصنَّف — لا فشل بدون سياق.

MUST: كل node يُطلق exception بكود محدد من `PlatformError` عند الفشل.
MUST: `INCONSISTENT_STATE` يُسجَّل في `inconsistent_states` ويُشعَر صاحب المشروع فوراً.
MUST: `INCONSISTENT_STATE` يُوقف كل workflow مستقبلي للقالب المعني حتى الحل اليدوي.
MUST NOT: لا exception يُبتلع بصمت — كل خطأ في logs مع timestamp وكود وسياق.
MUST NOT: لا `status = FAILED` بدون `error_code` مقابل له.

---

### IX. VIP Bundle — منتج مستقل
VIP Bundle كيان تجاري مستقل في Lemon Squeezy — ليس امتداداً لمنتج القالب.

MUST: VIP Bundle منتج Lemon Squeezy مستقل بـ `ls_product_id` و`ls_variant_id` خاصين.
MUST: كل قالب جديد يُضاف تلقائياً لـ `vip_registry.theme_slugs` في `VIP_CATALOG_UPDATER`.
MUST NOT: لا variant VIP داخل منتج القالب نفسه — أبداً.
MUST: `vip_registry` يُحدَّث قبل إطلاق `NEW_PRODUCT_LIVE`.

---

### X. Changelog Contract
Changelog عقد ملزم بصيغة محددة — النص الحر مرفوض برمجياً.

MUST: كل تحديث يحمل changelog صالحاً: `summary_ar` + `items_ar[]` + `type` + `is_security`.
MUST: `type` ∈ {"patch", "minor", "major"} — أي قيمة أخرى رفض بـ `PLT_803`.
MUST: التحديثات الأمنية (`is_security=true`) تتجاوز `email_opt_in` للمشترين.
MUST NOT: لا `THEME_UPDATED_LIVE` دون changelog صالح — الـ workflow يتوقف.

---

## Infrastructure Constraints

| المكوّن | الاستخدام | القيود |
|---------|-----------|--------|
| WordPress REST API | صفحات المنتج (ar_theme_product) | HTTPS فقط · Editor user · 60 req/min |
| Lemon Squeezy API | مدفوعات + تراخيص + variants | Source of truth للمبيعات |
| Resend | إيميلات الإشعارات | من STORE_EMAIL_FROM في .env |
| Redis Pub/Sub | إشعارات غير حرجة | best-effort delivery |
| Redis Streams | أحداث حرجة (theme-events, product-events, sales-events) | at-least-once · idempotent handlers |
| PostgreSQL | theme_registry, vip_registry, inconsistent_states, execution_log | مصدر الحقيقة |
| Python | 3.12 | — |
| Framework | LangGraph + FastAPI | — |

**Asset Timeout Policy** (غير قابل للتفاوض):
- 4 ساعات بلا assets → إشعار صاحب المشروع + خيارات
- تمديد واحد فقط (4 ساعات إضافية)
- 8 ساعات إجمالاً → إلغاء تلقائي لا رجعة فيه
- MUST NOT: لا نشر دون `screenshot` حتى لو قرّر صاحب المشروع المتابعة

**Human Review Limits**:
- MAX_REVISION_CYCLES = 3 (بعدها → LAUNCH_HOLD)
- HUMAN_REVIEW_TIMEOUT_HOURS = 48 (بعدها → PLT_501)

---

## Governance

**التسلسل الهرمي للمراجع** (تنازلياً):
1. هذه الوثيقة — Constitution (المرجع الأعلى للحوكمة)
2. `agents/platform/docs/spec.md` v3 — المواصفات التفصيلية
3. `docs/architecture.md` — المعمارية الجامعة لمنصة نافع
4. `.specify/memory/` — plan، tasks، checklist

**إجراء تعديل الدستور**:
- MAJOR: حذف مبدأ أو إعادة تعريفه جوهرياً → مراجعة بشرية إلزامية + تحديث spec.md
- MINOR: إضافة مبدأ جديد أو توسيع قائم → تحديث tasks.md وplan.md
- PATCH: توضيحات لفظية وتصحيحات → لا تحديثات تبعية إلزامية

**قائمة الامتثال — يُتحقق منها في كل مراجعة كود**:
- [ ] كل node يحمل `@idempotency_guard`
- [ ] كل حدث صادر يحمل `schema_version: "1.0"` و`event_id`
- [ ] `wp_post_id` غائب من كل الأحداث الواردة والصادرة
- [ ] كل `status = FAILED` مرفق بـ `error_code` من `PlatformError`
- [ ] `INCONSISTENT_STATE` يُوقف الـ workflow ويُشعر صاحب المشروع
- [ ] كل credentials في `.env` — لا في الكود

**Suggested commit message**:
`docs: ratify platform-agent constitution v1.1.0 (security split + INCONSISTENT_STATE gate)`

---

**Version**: 1.1.0 | **Ratified**: 2026-03-22 | **Last Amended**: 2026-03-22

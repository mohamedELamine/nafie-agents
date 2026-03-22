# API Contract — Platform Agent FastAPI

**Date**: 2026-03-22 | **Base URL**: `http://platform-agent:8000`
**Auth**: Internal network only (لا public exposure) — باستثناء `/webhooks/lemonsqueezy`

---

## Endpoints

### POST /webhooks/lemonsqueezy
استقبال Webhooks من Lemon Squeezy.

**Headers**:
```
X-Signature: sha256=<hmac-sha256-hex>
Content-Type: application/json
```

**Body**: Lemon Squeezy webhook payload (raw bytes للـ HMAC verification)

**Responses**:
```json
// 200 OK — webhook معالج بنجاح
{ "status": "ok" }

// 403 Forbidden — HMAC verification فشل
{ "error_code": "PLT_1001", "message": "Invalid webhook signature" }

// 422 — event_name غير مدعوم (يُتجاهل بصمت)
{ "status": "ignored", "reason": "unknown_event" }
```

**Rate Limit**: 60 req/min (من Lemon Squeezy فقط)

---

### GET /health
فحص حالة الوكيل.

**Response**:
```json
{
  "status": "ok",
  "agent": "platform",
  "version": "1.0.0",
  "timestamp": "2026-03-22T10:00:00Z"
}
```

---

### POST /review/{idempotency_key}
استقبال قرار مراجعة صاحب المشروع — يستأنف workflow من HUMAN_REVIEW_GATE.

**Path params**: `idempotency_key` — مثال: `launch:tayseer:1.0.0`

**Body**:
```json
{
  "decision": "approved_as_is",
  "notes": "",
  "edits": {}
}
```

**قيم `decision`**:
- `approved_as_is` — موافقة بدون تعديلات
- `approved_with_edits` — موافقة مع تعديلات في `edits`
- `needs_revision_minor` — تعديلات طفيفة (< 3 دورات)
- `needs_revision_major` — تعديلات جوهرية (< 3 دورات)
- `rejected` — رفض نهائي

**Responses**:
```json
// 200 OK
{ "status": "ok", "workflow_resumed": true }

// 404 — idempotency_key غير موجود
{ "error_code": "PLT_404", "message": "Workflow not found" }

// 409 — الـ workflow ليس في حالة WAITING_HUMAN_REVIEW
{ "error_code": "PLT_409", "message": "Workflow not awaiting review" }
```

---

### POST /assets/{idempotency_key}/decision
قرار صاحب المشروع بشأن الـ assets عند انتهاء المهلة الجزئية (4 ساعات).

**Path params**: `idempotency_key`

**Body**:
```json
{
  "decision": "proceed_with_available"
}
```

**قيم `decision`**:
- `proceed_with_available` — متابعة بالـ assets الموجودة
- `extend_wait` — تمديد 4 ساعات إضافية (مرة واحدة فقط)
- `cancel` — إلغاء الـ workflow

**Responses**:
```json
// 200 OK
{ "status": "ok", "decision": "proceed_with_available" }

// 400 — extend_wait طُلب مرتين
{ "error_code": "PLT_400", "message": "Extension already used" }
```

---

## Middleware

| الـ Middleware | التفاصيل |
|---------------|----------|
| Rate Limiting | 60 req/min (sliding window) |
| Request Logging | كل طلب يحمل `trace_id` عشوائي في الـ logs |
| Error Handler | كل exception → `{"error_code": "...", "message": "..."}` |
| HTTPS Enforcement | مُطبَّق على مستوى الـ reverse proxy (nginx) |

---

## Background Tasks

### AssetTimeoutWatchdog (كل 5 دقائق)

يفحص:
1. workflows في `WAITING_ASSETS` منذ > 4 ساعات → `POST /assets/{key}/decision` notification لصاحب المشروع
2. workflows في `WAITING_ASSETS` منذ > 8 ساعات → إلغاء تلقائي
3. reviews في `WAITING_HUMAN_REVIEW` منذ > 48 ساعة → `PLT_501`

---

**Version**: 1.0.0 | **Date**: 2026-03-22

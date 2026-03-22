---
description: "Phase 5: Commerce Event Consumer + FastAPI"
---

# Phase 5: Commerce Event Consumer

**Goal**: استقبال Webhooks من Lemon Squeezy وإطلاق أحداث على Redis
**Prerequisites**: Phase 2 مكتملة
**المرجع**: `agents/platform/docs/spec.md § ٨`

---

## Tasks (T070–T085)

### T070 — تعريف WEBHOOK_HANDLERS
**الملف**: `commerce/webhook_handler.py`

```python
WEBHOOK_HANDLERS = {
    "order_created":   self._handle_new_sale,
    "license_created": self._handle_license_issued,
}
```

---

### T071 — handle_webhook
**الملف**: `commerce/webhook_handler.py`

- استدعِ `_verify_signature(payload, signature)` أولاً
- إن فشل → رفع `PermissionError("PLT_1001")`
- وجّه لـ handler المناسب حسب `event["meta"]["event_name"]`

---

### T072 — _verify_signature
**الملف**: `commerce/webhook_handler.py`

```python
import hmac, hashlib, os

def _verify_signature(self, payload: bytes, signature: str) -> bool:
    secret  = os.environ["LS_WEBHOOK_SECRET"].encode()
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

### T073 — _handle_new_sale
**الملف**: `commerce/webhook_handler.py`

- استخرج من payload: `order_id`, `theme_slug`, `amount_usd`, `license_tier`, `occurred_at`
- أطلق `NEW_SALE` على Redis Stream `sales-events`:
  ```json
  {
    "event_type": "NEW_SALE",
    "schema_version": "1.0",
    "data": {
      "order_id": "...",
      "theme_slug": "...",
      "amount_usd": 29.0,
      "license_tier": "single",
      "occurred_at": "2026-03-16T12:00:00Z"
    }
  }
  ```

---

### T074 — _handle_license_issued
**الملف**: `commerce/webhook_handler.py`

- أطلق `LICENSE_ISSUED` على Redis Stream `sales-events`:
  ```json
  {
    "event_type": "LICENSE_ISSUED",
    "schema_version": "1.0",
    "data": {
      "license_id": "...",
      "theme_slug": "...",
      "license_tier": "single",
      "occurred_at": "..."
    }
  }
  ```

---

### T080 — FastAPI Webhook Endpoint
**الملف**: `api/main.py`

```python
@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request, x_signature: str = Header(...)):
    payload = await request.body()
    consumer.handle_webhook(payload, x_signature)
    return {"status": "ok"}
```

---

### T081 — [P] Health Check Endpoint
**الملف**: `api/main.py`

- `GET /health` → `{"status": "ok", "agent": "platform"}`

---

### T082 — Human Review Endpoint
**الملف**: `api/main.py` (endpoint جديد)

```python
@app.post("/review/{idempotency_key}")
async def submit_review(idempotency_key: str, decision: ReviewDecision, edits: dict = None):
```
- يستقبل قرار مراجعة صاحب المشروع
- يستأنف الـ workflow من HUMAN_REVIEW_GATE

---

### T083 — Asset Decision Endpoint
**الملف**: `api/main.py`

```python
@app.post("/assets/{idempotency_key}/decision")
async def asset_decision(idempotency_key: str, decision: str):
    # proceed_with_available | extend_wait | cancel
```

---

### T084 — [P] إضافة Middleware للـ FastAPI
- Rate limiting: 60 طلب/دقيقة
- Request logging مع trace_id
- Error handler موحد يُعيد كود الخطأ

---

### T085 — [P] Background Tasks للـ Timeouts
**الملف**: `api/background.py` (ملف جديد)

- Task يعمل كل 5 دقائق يفحص:
  - Workflows في `WAITING_ASSETS` منذ > 4 ساعات → أشعر صاحب المشروع
  - Workflows في `WAITING_ASSETS` منذ > 8 ساعات → إلغاء تلقائي
  - Reviews في `WAITING_HUMAN_REVIEW` منذ > 48 ساعة → `PLT_501`

**Checkpoint ✅**:
- POST `/webhooks/lemonsqueezy` مع payload صحيح → حدث على Redis
- POST `/review/{key}` → استئناف workflow

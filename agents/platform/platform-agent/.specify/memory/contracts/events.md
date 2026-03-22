# Event Contracts — Platform Agent

**Date**: 2026-03-22 | **Schema Version**: 1.0

كل حدث يلتزم بـ Event Envelope المشترك. `wp_post_id` محظور في كل `data`.

---

## Event Envelope (Base)

```json
{
  "event_id": "<uuid-v4>",
  "event_type": "<EVENT_TYPE>",
  "schema_version": "1.0",
  "occurred_at": "<ISO-8601>",
  "correlation_id": "<uuid-v4>",
  "data": { }
}
```

---

## Inbound Events (Platform Agent يستقبلها)

### THEME_APPROVED
**Stream**: `theme-events` | **المُشغِّل**: Launch Workflow

```json
{
  "event_type": "THEME_APPROVED",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "version": "1.0.0",
    "theme_contract": {
      "theme_name_ar": "تيسير",
      "domain": "fashion",
      "cluster": "ecommerce",
      "build_version": "1.0.0",
      "woocommerce_enabled": true,
      "cod_enabled": false
    },
    "package_path": "/builds/tayseer-1.0.0.zip",
    "approved_event_id": "<uuid-v4>",
    "build_id": "build-2026-03-22-001"
  }
}
```

**NOTE**: `wp_post_id` غائب — محظور.

---

### THEME_UPDATED
**Stream**: `theme-events` | **المُشغِّل**: Update Workflow

```json
{
  "event_type": "THEME_UPDATED",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "new_version": "1.1.0",
    "package_path": "/builds/tayseer-1.1.0.zip",
    "changelog": {
      "summary_ar": "تحسينات على صفحة المنتج وإصلاح خلل في الدفع",
      "items_ar": [
        "تحسين سرعة تحميل الصفحة الرئيسية",
        "إصلاح مشكلة الدفع عند استخدام الجوال"
      ],
      "type": "minor",
      "is_security": false
    },
    "event_id": "<uuid-v4>"
  }
}
```

---

### THEME_ASSETS_READY
**Stream**: `asset-events` | **المُشغِّل**: استئناف ASSET_WAITER

```json
{
  "event_type": "THEME_ASSETS_READY",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "version": "1.0.0",
    "idempotency_key": "launch:tayseer:1.0.0",
    "assets": {
      "screenshot": "/assets/tayseer/screenshot.webp",
      "preview_url": "https://preview.nafic.com/tayseer",
      "logo": "/assets/tayseer/logo.webp"
    }
  }
}
```

---

### THEME_ASSETS_PARTIALLY_READY
**Stream**: `asset-events`

```json
{
  "event_type": "THEME_ASSETS_PARTIALLY_READY",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "idempotency_key": "launch:tayseer:1.0.0",
    "available_assets": ["logo"],
    "missing_assets": ["screenshot"],
    "owner_decision_required": true
  }
}
```

---

## Outbound Events (Platform Agent يُطلقها)

### NEW_PRODUCT_LIVE
**Stream**: `product-events` | **Node**: LAUNCH_ANNOUNCER

```json
{
  "event_type": "NEW_PRODUCT_LIVE",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "theme_name_ar": "تيسير",
    "wp_post_url": "https://nafic.com/themes/tayseer",
    "ls_product_id": "ls-prod-12345",
    "pricing": {
      "single": 29,
      "unlimited": 79,
      "vip": 299
    },
    "final_score": 91,
    "launched_at": "2026-03-22T10:00:00Z"
  }
}
```

---

### THEME_UPDATED_LIVE
**Stream**: `product-events` | **Node**: UPDATE_ANNOUNCER

```json
{
  "event_type": "THEME_UPDATED_LIVE",
  "schema_version": "1.0",
  "data": {
    "theme_slug": "tayseer",
    "new_version": "1.1.0",
    "is_security": false,
    "buyers_notified": 42,
    "updated_at": "2026-03-22T11:00:00Z"
  }
}
```

---

### NEW_SALE
**Stream**: `sales-events` | **Node**: CommerceEventConsumer._handle_new_sale

```json
{
  "event_type": "NEW_SALE",
  "schema_version": "1.0",
  "data": {
    "order_id": "ls-order-99999",
    "theme_slug": "tayseer",
    "amount_usd": 29.0,
    "license_tier": "single",
    "occurred_at": "2026-03-22T12:00:00Z"
  }
}
```

---

### LICENSE_ISSUED
**Stream**: `sales-events` | **Node**: CommerceEventConsumer._handle_license_issued

```json
{
  "event_type": "LICENSE_ISSUED",
  "schema_version": "1.0",
  "data": {
    "license_id": "ls-lic-88888",
    "theme_slug": "tayseer",
    "license_tier": "single",
    "occurred_at": "2026-03-22T12:01:00Z"
  }
}
```

---

## Validation Rules

| الحقل | القاعدة |
|-------|---------|
| `event_id` | uuid-v4، غير قابل للتكرار |
| `schema_version` | `"1.0"` فقط (حالياً) |
| `occurred_at` | ISO-8601 UTC |
| `changelog.type` | `"patch"` \| `"minor"` \| `"major"` |
| `license_tier` | `"single"` \| `"unlimited"` \| `"vip"` |
| `wp_post_id` | **محظور** في كل `data` وارداً وصادراً |

---

**Version**: 1.0.0 | **Date**: 2026-03-22

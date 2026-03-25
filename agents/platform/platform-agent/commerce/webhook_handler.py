"""
Commerce Event Consumer — T070–T074
يستقبل Webhooks من Lemon Squeezy ويحوّلها إلى أحداث Redis.

Constitution VII: HMAC-SHA256 verification أول خطوة دائماً.
المرجع: spec.md § ٨ | tasks/phase5 § T070–T074
"""
from __future__ import annotations
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from services.redis_bus import RedisBus, STREAM_SALES_EVENTS

logger = logging.getLogger("platform_agent.commerce.webhook_handler")


class CommerceEventConsumer:
    WEBHOOK_HANDLERS = {
        "order_created":   "_handle_new_sale",
        "license_created": "_handle_license_issued",
    }

    def __init__(self, redis_bus: RedisBus) -> None:
        self.redis_bus = redis_bus

    # T071
    def handle_webhook(self, payload: bytes, signature: str) -> None:
        if not self._verify_signature(payload, signature):
            logger.warning("handle_webhook | PLT_1001 | invalid signature")
            raise PermissionError("PLT_1001: Invalid webhook signature")

        import json
        event = json.loads(payload)
        event_name = event.get("meta", {}).get("event_name", "")
        handler_name = self.WEBHOOK_HANDLERS.get(event_name)

        if not handler_name:
            logger.info("handle_webhook | unknown event_name=%s — ignored", event_name)
            return

        handler = getattr(self, handler_name)
        handler(event)

    # T072
    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        secret = os.environ["LS_WEBHOOK_SECRET"].encode()
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    # T073
    def _handle_new_sale(self, event: dict) -> None:
        data = event.get("data", {})
        attrs = data.get("attributes", {})
        order_id = str(data.get("id", ""))
        # استخرج theme_slug من custom_data
        custom = attrs.get("first_order_item", {}) or {}
        meta = event.get("meta", {}).get("custom_data", {})
        theme_slug = meta.get("theme_slug", "")
        amount = attrs.get("total", 0) / 100  # من cents
        variant_name = (custom.get("variant_name") or "single").lower()
        tier = "unlimited" if "unlimited" in variant_name else "single"

        redis_event = self.redis_bus.build_event(
            event_type="NEW_SALE",
            data={
                "order_id": order_id,
                "theme_slug": theme_slug,
                "amount_usd": round(amount, 2),
                "license_tier": tier,
                "occurred_at": attrs.get("created_at", datetime.now(tz=timezone.utc).isoformat()),
            },
        )
        self.redis_bus.publish_stream(STREAM_SALES_EVENTS, redis_event)
        logger.info("_handle_new_sale | order=%s theme=%s tier=%s amount=$%s",
                    order_id, theme_slug, tier, amount)

    # T074
    def _handle_license_issued(self, event: dict) -> None:
        data = event.get("data", {})
        attrs = data.get("attributes", {})
        license_id = str(data.get("id", ""))
        meta = event.get("meta", {}).get("custom_data", {})
        theme_slug = meta.get("theme_slug", "")
        variant_name = (attrs.get("variant_name") or "single").lower()
        tier = "unlimited" if "unlimited" in variant_name else "single"

        redis_event = self.redis_bus.build_event(
            event_type="LICENSE_ISSUED",
            data={
                "license_id": license_id,
                "theme_slug": theme_slug,
                "license_tier": tier,
                "occurred_at": attrs.get("created_at", datetime.now(tz=timezone.utc).isoformat()),
            },
        )
        self.redis_bus.publish_stream(STREAM_SALES_EVENTS, redis_event)
        logger.info("_handle_license_issued | license=%s theme=%s tier=%s",
                    license_id, theme_slug, tier)

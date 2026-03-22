"""
Commerce Event Consumer — Workflow 3
TODO: تنفيذ كامل (راجع tasks/phase5_commerce_consumer.md)
المرجع: agents/platform/docs/spec.md § ٨
"""
import hashlib
import hmac
import json
import os
from typing import Dict


class CommerceEventConsumer:
    """
    خدمة دائمة مستقلة — لا تتقاطع مع Workflows الأخرى.
    تستقبل Webhooks من Lemon Squeezy.
    """

    WEBHOOK_HANDLERS = {
        # TODO: T070 — ربط handlers بأنواع الأحداث
    }

    def handle_webhook(self, payload: bytes, signature: str) -> None:
        """TODO: T071 — التحقق من signature ثم توجيه الحدث"""
        if not self._verify_signature(payload, signature):
            raise PermissionError("PLT_1001: Webhook signature invalid")
        event   = json.loads(payload)
        handler = self.WEBHOOK_HANDLERS.get(event["meta"]["event_name"])
        if handler:
            handler(event)

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """TODO: T072 — HMAC-SHA256 verification"""
        raise NotImplementedError("TODO: T072")

    def _handle_new_sale(self, event: Dict) -> None:
        """TODO: T073 — معالجة NEW_SALE + إطلاق حدث على Redis"""
        raise NotImplementedError("TODO: T073")

    def _handle_license_issued(self, event: Dict) -> None:
        """TODO: T074 — معالجة LICENSE_ISSUED + إطلاق حدث على Redis"""
        raise NotImplementedError("TODO: T074")

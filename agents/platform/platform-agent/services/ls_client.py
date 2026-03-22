"""
Lemon Squeezy API Client
TODO: تنفيذ كامل (راجع tasks/phase2_foundation.md § T024–T028)
المرجع: agents/platform/docs/spec.md § ٩ (هيكل التراخيص)

PRICING:
  single:    $29  — 1 activation, 1 year
  unlimited: $79  — unlimited activations, 1 year
  vip:       $299 — unlimited, lifetime (منتج مستقل)
"""
import os
import requests
from typing import Dict, List, Optional


PRICING = {
    "single":    {"price": 29,  "activations": 1,    "duration": "1y"},
    "unlimited": {"price": 79,  "activations": None, "duration": "1y"},
    "vip":       {"price": 299, "activations": None, "duration": "lifetime"},
}


class LemonSqueezyClient:
    BASE_URL = "https://api.lemonsqueezy.com/v1"

    def __init__(self):
        self.api_key  = os.environ["LS_API_KEY"]
        self.store_id = os.environ["LS_STORE_ID"]
        self.headers  = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept":        "application/vnd.api+json",
            "Content-Type":  "application/vnd.api+json",
        }

    # TODO: T024
    def create_product(self, name_ar: str, theme_slug: str) -> Dict:
        """
        ينشئ منتجاً جديداً في المتجر (draft)
        يعيد: {"product_id": str, "single_variant_id": str, "unlimited_variant_id": str}
        """
        raise NotImplementedError("TODO: T024")

    # TODO: T025
    def activate_product(self, ls_product_id: str) -> bool:
        """ينشر المنتج — يُستدعى من SAGA_PUBLISHER"""
        raise NotImplementedError("TODO: T025")

    # TODO: T026
    def deactivate_product(self, ls_product_id: str) -> bool:
        """يُعيد المنتج لـ draft — Compensating action في Saga"""
        raise NotImplementedError("TODO: T026")

    # TODO: T027
    def update_product_file(self, ls_product_id: str, zip_path: str) -> bool:
        """يحدث ملف القالب — لـ Product Update Workflow"""
        raise NotImplementedError("TODO: T027")

    # TODO: T028
    def get_active_licenses(self, ls_product_id: str) -> List[Dict]:
        """جلب قائمة المشترين النشطين — لإرسال إشعارات التحديث"""
        raise NotImplementedError("TODO: T028")

    # TODO: T029
    def get_vip_product(self) -> Optional[Dict]:
        """جلب منتج VIP Bundle من المتجر"""
        raise NotImplementedError("TODO: T029")

    # TODO: T030
    def add_theme_to_vip(self, vip_product_id: str, theme_slug: str) -> bool:
        """إضافة القالب الجديد لـ VIP Bundle"""
        raise NotImplementedError("TODO: T030")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.BASE_URL}/{endpoint}"
        resp = requests.request(method, url, headers=self.headers,
                                timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

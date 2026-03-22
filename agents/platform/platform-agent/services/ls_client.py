"""
Lemon Squeezy API Client — T024–T030

الأسعار ثابتة (Constitution V — Price Immutability):
  single:    $29 USD — 1 activation, 1 year
  unlimited: $79 USD — unlimited activations, 1 year
  vip:       $299 USD — unlimited, lifetime (منتج مستقل)

المرجع: agents/platform/docs/spec.md § ٩، ١٠
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("platform_agent.services.ls_client")

# ─── الأسعار الثابتة — لا تُعدَّل بعد الإنشاء (Constitution V) ─────
PRICING: Dict[str, Dict[str, Any]] = {
    "single": {
        "price_usd_cents": 2900,          # $29.00
        "activation_limit": 1,
        "is_lifetime": False,
    },
    "unlimited": {
        "price_usd_cents": 7900,          # $79.00
        "activation_limit": None,          # unlimited
        "is_lifetime": False,
    },
    "vip": {
        "price_usd_cents": 29900,         # $299.00
        "activation_limit": None,
        "is_lifetime": True,
    },
}


class LemonSqueezyError(Exception):
    """خطأ في Lemon Squeezy API يحمل error_code."""

    def __init__(self, error_code: str, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class LemonSqueezyClient:
    """
    Wrapper على Lemon Squeezy REST API v1.

    Lemon Squeezy يستخدم JSON:API format.
    """

    BASE_URL = "https://api.lemonsqueezy.com/v1"

    def __init__(self) -> None:
        self.api_key = os.environ["LS_API_KEY"]
        self.store_id = os.environ["LS_STORE_ID"]

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    # ─────────────────────────────────────────────────────────
    # T024 — create_product
    # ─────────────────────────────────────────────────────────

    def create_product(self, name_ar: str, theme_slug: str) -> Dict[str, str]:
        """
        ينشئ منتجاً جديداً (status=draft) مع variant لـ Single و Unlimited.

        Args:
            name_ar: اسم القالب بالعربية.
            theme_slug: slug القالب (يُستخدم في الـ slug URL).

        Returns:
            {"product_id": str, "single_variant_id": str, "unlimited_variant_id": str}

        Raises:
            LemonSqueezyError(PLT_201) عند الفشل.
        """
        try:
            # 1. إنشاء المنتج
            product_payload = {
                "data": {
                    "type": "products",
                    "attributes": {
                        "name": name_ar,
                        "slug": theme_slug,
                        "status": "draft",
                        "store_id": int(self.store_id),
                        "description": f"قالب WordPress عربي احترافي — {name_ar}",
                    },
                    "relationships": {
                        "store": {
                            "data": {"type": "stores", "id": str(self.store_id)}
                        }
                    },
                }
            }
            resp = self._client.post("/products", json=product_payload)
            resp.raise_for_status()
            product_data = resp.json()
            product_id = product_data["data"]["id"]

            logger.info("ls.create_product | product_id=%s name=%s", product_id, name_ar)

            # 2. إنشاء variant Single ($29)
            single_id = self._create_variant(
                product_id=product_id,
                name="Single License",
                tier="single",
            )

            # 3. إنشاء variant Unlimited ($79)
            unlimited_id = self._create_variant(
                product_id=product_id,
                name="Unlimited License",
                tier="unlimited",
            )

            return {
                "product_id": product_id,
                "single_variant_id": single_id,
                "unlimited_variant_id": unlimited_id,
            }

        except httpx.HTTPStatusError as exc:
            logger.error(
                "ls.create_product failed | status=%s | %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
            raise LemonSqueezyError(
                "PLT_201",
                f"LS create_product failed: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("ls.create_product network error | %s", exc)
            raise LemonSqueezyError("PLT_201", f"LS network error: {exc}") from exc

    def _create_variant(
        self, product_id: str, name: str, tier: str
    ) -> str:
        """ينشئ variant واحد بسعره الثابت ويعيد الـ id."""
        pricing = PRICING[tier]
        payload = {
            "data": {
                "type": "variants",
                "attributes": {
                    "name": name,
                    "price": pricing["price_usd_cents"],
                    "is_subscription": False,
                    "has_license_keys": True,
                    "license_activation_limit": pricing["activation_limit"],
                    "is_license_limit_unlimited": pricing["activation_limit"] is None,
                    "license_length_value": None if pricing["is_lifetime"] else 1,
                    "license_length_unit": None if pricing["is_lifetime"] else "years",
                    "is_license_length_unlimited": pricing["is_lifetime"],
                },
                "relationships": {
                    "product": {
                        "data": {"type": "products", "id": product_id}
                    }
                },
            }
        }
        resp = self._client.post("/variants", json=payload)
        resp.raise_for_status()
        variant_id = resp.json()["data"]["id"]
        logger.info(
            "ls._create_variant | variant_id=%s tier=%s price=$%s",
            variant_id,
            tier,
            pricing["price_usd_cents"] / 100,
        )
        return variant_id

    # ─────────────────────────────────────────────────────────
    # T025 — activate_product
    # ─────────────────────────────────────────────────────────

    def activate_product(self, ls_product_id: str) -> bool:
        """
        ينشر المنتج (draft → published).

        يُستدعى من SAGA_PUBLISHER فقط — بعد نشر WordPress.

        Raises:
            LemonSqueezyError(PLT_201) عند الفشل.
        """
        try:
            resp = self._client.patch(
                f"/products/{ls_product_id}",
                json={
                    "data": {
                        "type": "products",
                        "id": ls_product_id,
                        "attributes": {"status": "published"},
                    }
                },
            )
            resp.raise_for_status()
            logger.info("ls.activate_product | product_id=%s | PUBLISHED", ls_product_id)
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "ls.activate_product failed | product_id=%s status=%s",
                ls_product_id,
                exc.response.status_code,
            )
            raise LemonSqueezyError(
                "PLT_201",
                f"LS activate failed: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc

    # ─────────────────────────────────────────────────────────
    # T026 — deactivate_product (Saga Compensating Action)
    # ─────────────────────────────────────────────────────────

    def deactivate_product(self, ls_product_id: str) -> bool:
        """
        يُعيد المنتج إلى draft — Compensating Action في Saga.

        لا يرفع exception عند الفشل — يعيد False ليُسجَّل INCONSISTENT_STATE.
        """
        try:
            resp = self._client.patch(
                f"/products/{ls_product_id}",
                json={
                    "data": {
                        "type": "products",
                        "id": ls_product_id,
                        "attributes": {"status": "draft"},
                    }
                },
            )
            resp.raise_for_status()
            logger.info(
                "ls.deactivate_product | product_id=%s | DRAFT (rollback)", ls_product_id
            )
            return True
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(
                "ls.deactivate_product ROLLBACK FAILED | product_id=%s | %s",
                ls_product_id,
                exc,
            )
            return False

    # ─────────────────────────────────────────────────────────
    # T027 — update_product_file
    # ─────────────────────────────────────────────────────────

    def update_product_file(self, ls_product_id: str, zip_path: str) -> bool:
        """
        يحدث الملف المرفق بمنتج Lemon Squeezy (ZIP القالب).

        الخطوات:
        1. جلب files الموجودة للمنتج
        2. حذف الملف القديم
        3. رفع الملف الجديد

        Raises:
            LemonSqueezyError(PLT_704) عند الفشل.
        """
        path = Path(zip_path)
        if not path.exists():
            raise LemonSqueezyError("PLT_704", f"الملف غير موجود: {zip_path}")

        try:
            # 1. جلب variant files الموجودة
            resp = self._client.get(
                "/files", params={"filter[product_id]": ls_product_id}
            )
            resp.raise_for_status()
            files_data = resp.json().get("data", [])

            # 2. حذف كل الملفات القديمة
            for file_obj in files_data:
                file_id = file_obj["id"]
                del_resp = self._client.delete(f"/files/{file_id}")
                if del_resp.status_code not in (200, 204):
                    logger.warning(
                        "ls.update_product_file | failed to delete old file %s", file_id
                    )

            # 3. رفع الملف الجديد (multipart — LS يقبل form upload)
            with path.open("rb") as f:
                upload_resp = self._client.post(
                    "/files",
                    data={"file[product_id]": ls_product_id},
                    files={"file": (path.name, f, "application/zip")},
                    headers={
                        "Accept": "application/vnd.api+json",
                        "Authorization": f"Bearer {self.api_key}",
                        # لا Content-Type — httpx يضبطه تلقائياً مع multipart
                    },
                )
            upload_resp.raise_for_status()
            logger.info(
                "ls.update_product_file | product_id=%s | file=%s",
                ls_product_id,
                path.name,
            )
            return True

        except httpx.HTTPStatusError as exc:
            logger.error(
                "ls.update_product_file failed | product_id=%s status=%s",
                ls_product_id,
                exc.response.status_code,
            )
            raise LemonSqueezyError(
                "PLT_704",
                f"LS file update failed: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            raise LemonSqueezyError("PLT_704", f"LS network error: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # T028 — get_active_licenses
    # ─────────────────────────────────────────────────────────

    def get_active_licenses(self, ls_product_id: str) -> List[Dict[str, Any]]:
        """
        جلب قائمة المشترين الذين لديهم رخص نشطة.

        يُستخدم في ELIGIBILITY_FILTER لتحديد من يستحق إشعار التحديث.

        Returns:
            list of {"email": str, "license_key": str, "tier": str}
        """
        try:
            licenses: List[Dict] = []
            page = 1

            while True:
                resp = self._client.get(
                    "/licenses",
                    params={
                        "filter[product_id]": ls_product_id,
                        "filter[status]": "active",
                        "page[size]": 100,
                        "page[number]": page,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data", [])

                for item in items:
                    attrs = item.get("attributes", {})
                    email = attrs.get("order_item", {}).get("customer_email", "")
                    if email:
                        licenses.append(
                            {
                                "email": email,
                                "license_key": attrs.get("key", ""),
                                "tier": attrs.get("variant_name", "single").lower(),
                                "status": attrs.get("status", ""),
                            }
                        )

                # pagination
                meta = data.get("meta", {}).get("page", {})
                if page >= meta.get("lastPage", 1):
                    break
                page += 1

            logger.info(
                "ls.get_active_licenses | product_id=%s | count=%s",
                ls_product_id,
                len(licenses),
            )
            return licenses

        except httpx.HTTPStatusError as exc:
            logger.error(
                "ls.get_active_licenses failed | product_id=%s status=%s",
                ls_product_id,
                exc.response.status_code,
            )
            return []  # يعيد قائمة فارغة — لا يوقف workflow

    # ─────────────────────────────────────────────────────────
    # T029 — get_vip_product
    # ─────────────────────────────────────────────────────────

    def get_vip_product(self) -> Optional[Dict[str, Any]]:
        """
        جلب بيانات منتج VIP Bundle من Lemon Squeezy.

        يبحث أولاً بـ LS_VIP_PRODUCT_ID من .env.

        Returns:
            {"id": str, "name": str, "status": str} أو None إذا لم يُوجد.
        """
        vip_id = os.getenv("LS_VIP_PRODUCT_ID")
        if not vip_id:
            logger.warning("ls.get_vip_product | LS_VIP_PRODUCT_ID غير مُعيَّن")
            return None

        try:
            resp = self._client.get(f"/products/{vip_id}")
            resp.raise_for_status()
            data = resp.json()["data"]
            return {
                "id": data["id"],
                "name": data["attributes"].get("name", ""),
                "status": data["attributes"].get("status", ""),
            }
        except httpx.HTTPStatusError as exc:
            logger.error(
                "ls.get_vip_product failed | vip_id=%s status=%s",
                vip_id,
                exc.response.status_code,
            )
            return None

    # ─────────────────────────────────────────────────────────
    # T030 — add_theme_to_vip
    # ─────────────────────────────────────────────────────────

    def add_theme_to_vip(self, vip_product_id: str, theme_slug: str) -> bool:
        """
        يُحدّث وصف VIP Bundle بإضافة ذكر القالب الجديد.

        ملاحظة: Lemon Squeezy لا يدعم product bundling API مباشرة.
        التحديث هنا يمس الـ description فقط — الـ vip_registry هي السجل الفعلي.

        Returns:
            True عند النجاح، False عند الفشل (لا يوقف workflow).
        """
        try:
            # جلب الوصف الحالي
            resp = self._client.get(f"/products/{vip_product_id}")
            resp.raise_for_status()
            current = resp.json()["data"]["attributes"]
            current_desc = current.get("description", "")

            # لا نضيف إذا كان موجوداً
            if theme_slug in current_desc:
                logger.info(
                    "ls.add_theme_to_vip | %s already in VIP description", theme_slug
                )
                return True

            new_desc = f"{current_desc}\n- {theme_slug}".strip()
            patch_resp = self._client.patch(
                f"/products/{vip_product_id}",
                json={
                    "data": {
                        "type": "products",
                        "id": vip_product_id,
                        "attributes": {"description": new_desc},
                    }
                },
            )
            patch_resp.raise_for_status()
            logger.info(
                "ls.add_theme_to_vip | product_id=%s | added=%s",
                vip_product_id,
                theme_slug,
            )
            return True
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(
                "ls.add_theme_to_vip failed | product_id=%s | %s", vip_product_id, exc
            )
            return False

    # ─────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "LemonSqueezyClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

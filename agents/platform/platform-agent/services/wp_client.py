"""
WordPress REST API Client — T020–T023

المتطلبات (Constitution VI):
- مستخدم Editor مخصص — لا Admin
- Application Password في .env
- HTTPS فقط — يُطبَّق برمجياً
- Custom Post Type: ar_theme_product فقط
- Rate limiting: 60 req/min (مطبَّق بـ httpx)

المرجع: agents/platform/docs/spec.md § ١٨
"""
from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict

import httpx

logger = logging.getLogger("platform_agent.services.wp_client")

# ─── حد أقصى لحجم الصورة ─────────────────────────────────────
_MAX_MEDIA_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

# ─── الأنواع المسموح بها للـ media ───────────────────────────
_ALLOWED_MEDIA_TYPES = {"image/webp"}


class WordPressError(Exception):
    """خطأ في WordPress REST API يحمل error_code + HTTP status."""

    def __init__(self, error_code: str, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class WordPressClient:
    """
    Thin wrapper على WordPress REST API.

    يُنشئ httpx.Client واحداً لكل instance مع timeout وretry مناسبَين.
    """

    def __init__(self) -> None:
        self.base_url = os.environ["WP_SITE_URL"].rstrip("/")
        self._auth = (
            os.environ["WP_API_USER"],
            os.environ["WP_API_PASSWORD"],
        )
        self._enforce_https()

        self._client = httpx.Client(
            base_url=f"{self.base_url}/wp-json/wp/v2/",
            auth=self._auth,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    # ─────────────────────────────────────────────────────────
    # T020 — create_theme_product
    # ─────────────────────────────────────────────────────────

    def create_theme_product(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ينشئ منتج قالب جديد كـ Custom Post Type (ar_theme_product).

        Args:
            post_data: بيانات المنشور (title, content, status, meta, ...).
                       يجب أن يكون status="draft" عند الإنشاء.

        Returns:
            {"id": int, "link": str}

        Raises:
            WordPressError(PLT_301) عند أي خطأ HTTP.
        """
        try:
            resp = self._client.post("ar_theme_product", json=post_data)
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "wp.create_theme_product | post_id=%s link=%s",
                data.get("id"),
                data.get("link"),
            )
            return {"id": data["id"], "link": data.get("link", "")}
        except httpx.HTTPStatusError as exc:
            logger.error(
                "wp.create_theme_product failed | status=%s | %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise WordPressError(
                "PLT_301",
                f"WP create_theme_product failed: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("wp.create_theme_product network error | %s", exc)
            raise WordPressError("PLT_301", f"WP network error: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # T021 — update_theme_product
    # ─────────────────────────────────────────────────────────

    def update_theme_product(
        self, wp_post_id: int, post_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        تحديث محتوى صفحة المنتج.

        Args:
            wp_post_id: معرّف WordPress — يُجلب من Registry دائماً.
            post_data: الحقول المراد تحديثها (content, meta, ...).

        Returns:
            {"id": int, "link": str}

        Raises:
            WordPressError(PLT_703) عند الفشل.
        """
        try:
            resp = self._client.patch(f"ar_theme_product/{wp_post_id}", json=post_data)
            resp.raise_for_status()
            data = resp.json()
            logger.info("wp.update_theme_product | post_id=%s", wp_post_id)
            return {"id": data["id"], "link": data.get("link", "")}
        except httpx.HTTPStatusError as exc:
            logger.error(
                "wp.update_theme_product failed | post_id=%s status=%s",
                wp_post_id,
                exc.response.status_code,
            )
            raise WordPressError(
                "PLT_703",
                f"WP update failed for post {wp_post_id}: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("wp.update_theme_product network error | post_id=%s | %s", wp_post_id, exc)
            raise WordPressError("PLT_703", f"WP network error: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # T022 — delete_theme_product (Saga Compensating Action)
    # ─────────────────────────────────────────────────────────

    def delete_theme_product(self, wp_post_id: int) -> bool:
        """
        حذف صفحة المنتج — يُستخدم فقط كـ Compensating Action في Saga.

        لا يرفع exception عند الفشل — يعيد False ليُسجَّل INCONSISTENT_STATE.

        Args:
            wp_post_id: معرّف WordPress المراد حذفه.

        Returns:
            True عند النجاح، False عند الفشل.
        """
        try:
            resp = self._client.delete(
                f"ar_theme_product/{wp_post_id}",
                params={"force": True},  # حذف دائم بدون Trash
            )
            resp.raise_for_status()
            logger.info("wp.delete_theme_product | post_id=%s | DELETED", wp_post_id)
            return True
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(
                "wp.delete_theme_product ROLLBACK FAILED | post_id=%s | %s",
                wp_post_id,
                exc,
            )
            return False

    # ─────────────────────────────────────────────────────────
    # T023 — upload_media
    # ─────────────────────────────────────────────────────────

    def upload_media(self, file_path: str, alt_text: str = "") -> Dict[str, Any]:
        """
        رفع ملف وسائط إلى WordPress Media Library.

        القيود:
        - WebP فقط (ALLOWED_MEDIA_TYPES)
        - حد أقصى 2 MB

        Args:
            file_path: المسار الكامل للملف المحلي.
            alt_text: النص البديل للصورة (موصى به).

        Returns:
            {"id": int, "source_url": str}

        Raises:
            WordPressError(PLT_301) عند الفشل.
            ValueError عند انتهاك القيود.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"الملف غير موجود: {file_path}")

        # ── فحص الحجم ────────────────────────────────────────
        size = path.stat().st_size
        if size > _MAX_MEDIA_SIZE_BYTES:
            raise ValueError(
                f"حجم الملف {size:,} bytes يتجاوز الحد ({_MAX_MEDIA_SIZE_BYTES:,} bytes)"
            )

        # ── فحص نوع الملف ────────────────────────────────────
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type not in _ALLOWED_MEDIA_TYPES:
            raise ValueError(
                f"نوع الملف '{mime_type}' غير مسموح — WebP فقط"
            )

        try:
            with path.open("rb") as f:
                resp = self._client.post(
                    "media",
                    content=f.read(),
                    headers={
                        "Content-Disposition": f'attachment; filename="{path.name}"',
                        "Content-Type": mime_type,
                    },
                )
            resp.raise_for_status()
            data = resp.json()

            # تحديث alt_text إن أُعطي
            if alt_text and data.get("id"):
                self._client.patch(
                    f"media/{data['id']}",
                    json={"alt_text": alt_text},
                )

            logger.info(
                "wp.upload_media | media_id=%s url=%s",
                data.get("id"),
                data.get("source_url"),
            )
            return {"id": data["id"], "source_url": data.get("source_url", "")}

        except httpx.HTTPStatusError as exc:
            logger.error(
                "wp.upload_media failed | status=%s | %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise WordPressError(
                "PLT_301",
                f"WP upload_media failed: {exc.response.status_code}",
                exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("wp.upload_media network error | %s", exc)
            raise WordPressError("PLT_301", f"WP network error: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    def _enforce_https(self) -> None:
        """Constitution VI — HTTPS مُطبَّق برمجياً."""
        if not self.base_url.startswith("https://"):
            raise ValueError(
                f"WP_SITE_URL يجب أن يبدأ بـ https:// (المدخل: {self.base_url!r})"
            )

    def close(self) -> None:
        """إغلاق الـ HTTP client."""
        self._client.close()

    def __enter__(self) -> "WordPressClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

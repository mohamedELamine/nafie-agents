"""
Product Registry — Single Source of Truth للقوالب المنشورة.

القاعدة الحرجة: wp_post_id يُجلب من هنا فقط — لا من الأحداث الواردة أبداً.
المرجع: agents/platform/docs/spec.md § ٤، ٥
data-model.md v1.0.0
"""
from __future__ import annotations

import json
import logging
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger("platform_agent.db.registry")


class RegistryError(Exception):
    """خطأ في عمليات Registry — يحمل error_code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


class ProductRegistry:
    """
    واجهة PostgreSQL للـ theme_registry.

    يستقبل `get_conn` — callable يُعيد context manager لاتصال DB (Law II).
    كل عملية تحصل على اتصال مستقل من الـ pool عبر `with self._get_conn() as conn`.
    """

    def __init__(
        self,
        get_conn: Callable[[], AbstractContextManager[psycopg2.extensions.connection]],
    ) -> None:
        self._get_conn = get_conn

    # ─────────────────────────────────────────────────────────
    # T010 — exists
    # ─────────────────────────────────────────────────────────

    def exists(self, theme_slug: str) -> bool:
        """
        هل القالب مُسجَّل في theme_registry؟

        Returns:
            True إذا وُجد، False إذا لم يُوجد.
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM theme_registry WHERE theme_slug = %s LIMIT 1",
                    (theme_slug,),
                )
                return cur.fetchone() is not None

    # ─────────────────────────────────────────────────────────
    # T011 — get
    # ─────────────────────────────────────────────────────────

    def get(self, theme_slug: str) -> Optional[Dict[str, Any]]:
        """
        جلب السجل الكامل للقالب — wp_post_id من هنا فقط.

        Returns:
            dict يحتوي جميع حقول theme_registry، أو None إذا لم يُوجد.
        """
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM theme_registry WHERE theme_slug = %s",
                    (theme_slug,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return dict(row)

    # ─────────────────────────────────────────────────────────
    # T012 — save
    # ─────────────────────────────────────────────────────────

    def save(self, record: Dict[str, Any]) -> None:
        """
        حفظ ThemeRecord جديد مع Provenance كامل.

        يرفع RegistryError(PLT_401) عند فشل الحفظ.

        Args:
            record: dict يحتوي جميع حقول ThemeRecord (انظر data-model.md).
        """
        sql = """
            INSERT INTO theme_registry (
                theme_slug, theme_name_ar, domain, cluster,
                woocommerce_enabled, cod_enabled,
                wp_post_id, wp_post_url,
                ls_product_id, ls_single_variant, ls_unlimited_variant,
                current_version, contract_version,
                build_id, approved_event_id, launch_idempotency_key,
                created_at, updated_at
            ) VALUES (
                %(theme_slug)s, %(theme_name_ar)s, %(domain)s, %(cluster)s,
                %(woocommerce_enabled)s, %(cod_enabled)s,
                %(wp_post_id)s, %(wp_post_url)s,
                %(ls_product_id)s, %(ls_single_variant)s, %(ls_unlimited_variant)s,
                %(current_version)s, %(contract_version)s,
                %(build_id)s, %(approved_event_id)s, %(launch_idempotency_key)s,
                NOW(), NOW()
            )
            ON CONFLICT (launch_idempotency_key) DO NOTHING
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, record)
                conn.commit()
            logger.info(
                "registry.save | theme=%s version=%s wp_post_id=%s",
                record.get("theme_slug"),
                record.get("current_version"),
                record.get("wp_post_id"),
            )
        except psycopg2.Error as exc:
            logger.error("registry.save failed | theme=%s | %s", record.get("theme_slug"), exc)
            raise RegistryError("PLT_401", f"Failed to save ThemeRecord: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # T013 — update_version
    # ─────────────────────────────────────────────────────────

    def update_version(
        self,
        theme_slug: str,
        new_version: str,
        event_id: str,
        idempotency_key: str,
    ) -> None:
        """
        تحديث إصدار القالب بعد Update Workflow ناجح.

        يحدّث: current_version, last_updated_at,
                last_update_event_id, last_update_idempotency_key, updated_at.
        """
        sql = """
            UPDATE theme_registry SET
                current_version             = %s,
                last_updated_at             = NOW(),
                last_update_event_id        = %s,
                last_update_idempotency_key = %s,
                updated_at                  = NOW()
            WHERE theme_slug = %s
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (new_version, event_id, idempotency_key, theme_slug))
                conn.commit()
            logger.info(
                "registry.update_version | theme=%s → v%s",
                theme_slug,
                new_version,
            )
        except psycopg2.Error as exc:
            logger.error(
                "registry.update_version failed | theme=%s | %s", theme_slug, exc
            )
            raise RegistryError("PLT_401", f"Failed to update version: {exc}") from exc

    # ─────────────────────────────────────────────────────────
    # T014 — has_unresolved_inconsistency
    # ─────────────────────────────────────────────────────────

    def has_unresolved_inconsistency(self, theme_slug: str) -> bool:
        """
        هل يوجد INCONSISTENT_STATE غير محلول لهذا القالب؟

        True → يوقف كل workflow جديد حتى التدخل البشري (Constitution VIII).
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM inconsistent_states
                    WHERE theme_slug = %s AND resolved_at IS NULL
                    LIMIT 1
                    """,
                    (theme_slug,),
                )
                return cur.fetchone() is not None

    # ─────────────────────────────────────────────────────────
    # T015 — record_inconsistent_state
    # ─────────────────────────────────────────────────────────

    def record_inconsistent_state(
        self,
        theme_slug: str,
        wp_state: Dict[str, Any],
        ls_state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        تسجيل حالة INCONSISTENT_STATE في قاعدة البيانات.

        يُسجَّل دائماً حتى عند فشل الإشعار — التسجيل أولوية قصوى.
        """
        sql = """
            INSERT INTO inconsistent_states
                (theme_slug, error_code, wp_state, ls_state, context, created_at)
            VALUES (%s, 'PLT_303', %s, %s, %s, NOW())
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        (
                            theme_slug,
                            json.dumps(wp_state),
                            json.dumps(ls_state),
                            json.dumps(context or {}),
                        ),
                    )
                conn.commit()
            logger.critical(
                "INCONSISTENT_STATE recorded | theme=%s | wp=%s ls=%s",
                theme_slug,
                wp_state,
                ls_state,
            )
        except psycopg2.Error as exc:
            # نُسجّل الخطأ لكن لا نُوقف — التسجيل أهم من الإيقاف
            logger.critical(
                "CRITICAL: Failed to record inconsistent state | theme=%s | %s",
                theme_slug,
                exc,
            )

    # ─────────────────────────────────────────────────────────
    # T016 — get_all_published
    # ─────────────────────────────────────────────────────────

    def get_all_published(self) -> List[Dict[str, Any]]:
        """
        جلب جميع القوالب المنشورة — يُستخدم من analytics agent.
        """
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM theme_registry ORDER BY created_at DESC"
                )
                return [dict(row) for row in cur.fetchall()]

    # ─────────────────────────────────────────────────────────
    # T017 — get_launch_date
    # ─────────────────────────────────────────────────────────

    def get_launch_date(self, theme_slug: str) -> Optional[datetime]:
        """
        تاريخ إطلاق القالب (created_at) — لحسابات analytics.
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT created_at FROM theme_registry WHERE theme_slug = %s",
                    (theme_slug,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    # ─────────────────────────────────────────────────────────
    # T018 — count_published
    # ─────────────────────────────────────────────────────────

    def count_published(self) -> int:
        """عدد القوالب المنشورة."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM theme_registry")
                row = cur.fetchone()
                return row[0] if row else 0

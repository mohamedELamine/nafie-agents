"""
Idempotency Guard — T019
Decorator على كل LangGraph node لمنع التنفيذ المكرر.

الخوارزمية:
  1. تحقق من execution_log بـ (idempotency_key, node_name, status="completed")
  2. إن وُجد → تجاوز التنفيذ وأعد state كما هو
  3. إلا → سجّل "started" → نفّذ → سجّل "completed"

المرجع: agents/platform/docs/spec.md § ٥
constitution.md المبدأ III
"""
from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable

import psycopg2

logger = logging.getLogger("platform_agent.db.idempotency")


# ─────────────────────────────────────────────────────────────
# Functional helpers — لاستخدامها داخل LangGraph nodes (closures)
# ─────────────────────────────────────────────────────────────

def check_completed(
    db_conn: psycopg2.extensions.connection, ikey: str, node_name: str
) -> bool:
    """True إذا كان الـ node قد أكمل تنفيذه سابقاً."""
    if not ikey:
        return False
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM execution_log
            WHERE idempotency_key = %s AND node_name = %s AND status = 'completed'
            LIMIT 1
            """,
            (ikey, node_name),
        )
        return cur.fetchone() is not None


def mark_started(
    db_conn: psycopg2.extensions.connection, ikey: str, node_name: str
) -> None:
    _log_started(db_conn, ikey, node_name)


def mark_completed(
    db_conn: psycopg2.extensions.connection,
    ikey: str,
    node_name: str,
    state: dict,
) -> None:
    _log_completed(db_conn, ikey, node_name, state)


def mark_failed(
    db_conn: psycopg2.extensions.connection, ikey: str, node_name: str
) -> None:
    _log_failed(db_conn, ikey, node_name)


def idempotency_guard(node_name: str) -> Callable:
    """
    Decorator factory.

    Usage:
        @idempotency_guard("PRODUCT_CREATOR")
        def product_creator(state: LaunchState, db_conn, ...) -> LaunchState:
            ...

    الـ node يجب أن يقبل `db_conn` كـ keyword argument أو الـ state يحمله.
    لاحظ: idempotency_key مأخوذ من state["idempotency_key"].
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(state: dict, *args: Any, **kwargs: Any) -> dict:
            db_conn: psycopg2.extensions.connection = kwargs.get("db_conn") or args[0]
            ikey: str = state.get("idempotency_key", "")

            if not ikey:
                logger.warning(
                    "idempotency_guard | node=%s | idempotency_key فارغ — تخطّي الحماية",
                    node_name,
                )
                return fn(state, *args, **kwargs)

            # ── فحص هل تم التنفيذ سابقاً؟ ──────────────────────────
            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT result_snapshot FROM execution_log
                    WHERE idempotency_key = %s
                      AND node_name       = %s
                      AND status          = 'completed'
                    LIMIT 1
                    """,
                    (ikey, node_name),
                )
                row = cur.fetchone()

            if row is not None:
                logger.info(
                    "idempotency_guard | SKIP (already completed) | node=%s key=%s",
                    node_name,
                    ikey,
                )
                # استعادة الـ state من snapshot (إن كان محفوظاً)
                if row[0]:
                    try:
                        snapshot = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        return {**state, **snapshot}
                    except (json.JSONDecodeError, TypeError):
                        pass
                return state

            # ── تسجيل البدء ─────────────────────────────────────────
            _log_started(db_conn, ikey, node_name)

            # ── تنفيذ الـ node الفعلي ────────────────────────────────
            try:
                result_state: dict = fn(state, *args, **kwargs)
            except Exception:
                _log_failed(db_conn, ikey, node_name)
                raise

            # ── تسجيل الاكتمال ──────────────────────────────────────
            _log_completed(db_conn, ikey, node_name, result_state)

            return result_state

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _log_started(
    db_conn: psycopg2.extensions.connection, ikey: str, node_name: str
) -> None:
    """تسجيل بداية التنفيذ في execution_log."""
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execution_log (idempotency_key, node_name, status, started_at)
                VALUES (%s, %s, 'started', NOW())
                ON CONFLICT (idempotency_key) DO UPDATE
                    SET node_name  = EXCLUDED.node_name,
                        status     = 'started',
                        started_at = NOW()
                """,
                (ikey, node_name),
            )
        db_conn.commit()
    except psycopg2.Error as exc:
        logger.warning("idempotency_guard | log_started failed | %s", exc)
        db_conn.rollback()


def _log_completed(
    db_conn: psycopg2.extensions.connection,
    ikey: str,
    node_name: str,
    state: dict,
) -> None:
    """تسجيل اكتمال التنفيذ مع snapshot خفيف من state."""
    # نحفظ حقول مهمة فقط — لا نحفظ كامل state
    snapshot = {
        k: v for k, v in state.items()
        if k in (
            "ls_product_id",
            "ls_single_variant_id",
            "ls_unlimited_variant_id",
            "wp_post_id",
            "wp_post_url",
            "status",
            "error_code",
        )
    }
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE execution_log SET
                    status              = 'completed',
                    last_completed_node = %s,
                    result_snapshot     = %s,
                    completed_at        = NOW()
                WHERE idempotency_key = %s
                """,
                (node_name, json.dumps(snapshot, default=str), ikey),
            )
        db_conn.commit()
        logger.debug("idempotency_guard | completed | node=%s key=%s", node_name, ikey)
    except psycopg2.Error as exc:
        logger.warning("idempotency_guard | log_completed failed | %s", exc)
        db_conn.rollback()


def _log_failed(
    db_conn: psycopg2.extensions.connection, ikey: str, node_name: str
) -> None:
    """تسجيل فشل التنفيذ — يُتيح إعادة المحاولة في الـ run التالي."""
    try:
        with db_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE execution_log SET
                    status       = 'failed',
                    completed_at = NOW()
                WHERE idempotency_key = %s
                """,
                (ikey,),
            )
        db_conn.commit()
    except psycopg2.Error as exc:
        logger.warning("idempotency_guard | log_failed failed | %s", exc)
        db_conn.rollback()

"""
Idempotency Guard — وكيل المحتوى
يمنع التوليد المزدوج لنفس الطلب.
المرجع: spec.md § ٢٠
All DB access goes through get_conn() (Law II).
All writes use ON CONFLICT DO NOTHING (Law III).
"""
from __future__ import annotations

from typing import Optional

from db.connection import get_conn
from logging_config import get_logger

logger = get_logger("db.idempotency")


def check_completed(ikey: str) -> bool:
    """True إن كان الطلب مكتملاً مسبقاً."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM content_execution_log WHERE idempotency_key = %s",
                [ikey],
            )
            row = cur.fetchone()
            if row and row[0] == "completed":
                logger.info("idempotency.skip key=%s status=completed", ikey)
                return True
            return False


def mark_started(ikey: str, node_name: str) -> None:
    """يُسجّل بدء معالجة الطلب. Law III: DO NOTHING if already exists."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO content_execution_log (idempotency_key, node_name, status, started_at)
                VALUES (%s, %s, 'started', NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
            """, [ikey, node_name])
        conn.commit()


def mark_completed(
    ikey:       str,
    node_name:  str,
    content_id: Optional[str] = None,
) -> None:
    """يُسجّل اكتمال الطلب."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE content_execution_log
                SET status = 'completed', node_name = %s,
                    content_id = %s, completed_at = NOW()
                WHERE idempotency_key = %s AND status != 'completed'
            """, [node_name, content_id, ikey])
        conn.commit()


def mark_failed(
    ikey:         str,
    node_name:    str,
    error_code:   str,
    error_detail: str,
) -> None:
    """يُسجّل فشل الطلب."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE content_execution_log
                SET status = 'failed', node_name = %s,
                    error_code = %s, error_detail = %s, failed_at = NOW()
                WHERE idempotency_key = %s AND status != 'completed'
            """, [node_name, error_code, error_detail, ikey])
        conn.commit()

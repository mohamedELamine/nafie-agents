"""
Idempotency Guard — وكيل المحتوى
يمنع التوليد المزدوج لنفس الطلب.
المرجع: spec.md § ٢٠
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger("content_agent.db.idempotency")


def _get_conn(dsn: str) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    return conn


def check_completed(ikey: str, dsn: Optional[str] = None) -> bool:
    """True إن كان الطلب مكتملاً مسبقاً."""
    _dsn = dsn or os.environ["DATABASE_URL"]
    conn = _get_conn(_dsn)
    try:
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
    finally:
        conn.close()


def mark_started(ikey: str, node_name: str, dsn: Optional[str] = None) -> None:
    """يُسجّل بدء معالجة الطلب."""
    _dsn = dsn or os.environ["DATABASE_URL"]
    conn = _get_conn(_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO content_execution_log (idempotency_key, node_name, status, started_at)
                VALUES (%s, %s, 'started', NOW())
                ON CONFLICT (idempotency_key) DO UPDATE
                SET status = 'started', node_name = %s, started_at = NOW()
            """, [ikey, node_name, node_name])
        conn.commit()
    finally:
        conn.close()


def mark_completed(
    ikey:       str,
    node_name:  str,
    content_id: Optional[str] = None,
    dsn:        Optional[str] = None,
) -> None:
    """يُسجّل اكتمال الطلب."""
    _dsn = dsn or os.environ["DATABASE_URL"]
    conn = _get_conn(_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE content_execution_log
                SET status = 'completed', node_name = %s,
                    content_id = %s, completed_at = NOW()
                WHERE idempotency_key = %s
            """, [node_name, content_id, ikey])
        conn.commit()
    finally:
        conn.close()


def mark_failed(
    ikey:         str,
    node_name:    str,
    error_code:   str,
    error_detail: str,
    dsn:          Optional[str] = None,
) -> None:
    """يُسجّل فشل الطلب."""
    _dsn = dsn or os.environ["DATABASE_URL"]
    conn = _get_conn(_dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE content_execution_log
                SET status = 'failed', node_name = %s,
                    error_code = %s, error_detail = %s, failed_at = NOW()
                WHERE idempotency_key = %s
            """, [node_name, error_code, error_detail, ikey])
        conn.commit()
    finally:
        conn.close()

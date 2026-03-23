"""
Connection pool مركزي — كل المكونات تستخدم get_conn() بدل hardcoded URLs.
"""
import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool

from ..logging_config import get_logger

logger = get_logger("db.connection")

_pool: pool.SimpleConnectionPool | None = None


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    """يُستدعى مرة واحدة عند startup من lifespan."""
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    _pool = pool.SimpleConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        dsn=database_url,
    )
    logger.info("Database connection pool initialized")


def close_pool() -> None:
    """يُستدعى عند shutdown."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager يُعيد connection من الـ pool ويُعيده بعد الانتهاء.

    Usage:
        with get_conn() as conn:
            event_store.save_event(conn, event)
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")

    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

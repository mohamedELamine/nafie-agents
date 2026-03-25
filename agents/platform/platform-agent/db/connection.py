"""
Connection pool مركزي — Platform Agent.
كل الاتصالات بـ DB تمر عبر get_conn() context manager (Law II).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool

from ..logging_config import get_logger

logger = get_logger("db.connection")

_pool: pool.SimpleConnectionPool | None = None


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    """يُستدعى مرة واحدة عند startup."""
    global _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    _pool = pool.SimpleConnectionPool(minconn, maxconn, dsn)
    logger.info(f"Platform DB connection pool initialised (min={minconn}, max={maxconn})")


def close_pool() -> None:
    """يُستدعى عند shutdown."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Platform DB connection pool closed")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager يُعيد connection من الـ pool ويُعيده بعد الانتهاء.

    Usage:
        with get_conn() as conn:
            registry = ProductRegistry(conn)
            ...
    """
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

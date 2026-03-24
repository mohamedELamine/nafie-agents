"""
Connection pool for visual-production-agent.
All DB access must go through get_conn() — Constitutional Law II.
"""
import logging
import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool

logger = logging.getLogger("visual_production.db.connection")

_pool: pool.SimpleConnectionPool | None = None

def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    global _pool
    dsn = os.environ.get("VISUAL_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("VISUAL_DATABASE_URL or DATABASE_URL environment variable is not set")
    _pool = pool.SimpleConnectionPool(minconn, maxconn, dsn=dsn)
    logger.info("Visual-production DB pool initialised")


def close_pool() -> None:
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Visual-production DB pool closed")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

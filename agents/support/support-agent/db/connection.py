"""
PostgreSQL connection pool for support-agent.
نفس نمط analytics-agent و marketing-agent.
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
    """Initialise the global connection pool (call once at startup)."""
    global _pool
    dsn = os.environ.get("SUPPORT_DATABASE_URL")
    if not dsn:
        raise RuntimeError("SUPPORT_DATABASE_URL environment variable is not set")
    _pool = pool.SimpleConnectionPool(minconn, maxconn, dsn)
    logger.info(f"Connection pool initialised (min={minconn}, max={maxconn})")


def close_pool() -> None:
    """Close all connections in the pool (call on shutdown)."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Connection pool closed")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context-manager: checks out a connection and returns it when done."""
    if _pool is None:
        raise RuntimeError("Connection pool is not initialised — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

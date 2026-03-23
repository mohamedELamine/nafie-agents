"""
Connection pool for content-agent.
All DB access must go through get_conn() — Constitutional Law II.
"""
import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool

from logging_config import get_logger

logger = get_logger("db.connection")

_pool: pool.SimpleConnectionPool | None = None


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    """Initialise the global connection pool (call once at startup)."""
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    _pool = pool.SimpleConnectionPool(minconn, maxconn, dsn=database_url)
    logger.info("Content-agent DB pool initialised")


def close_pool() -> None:
    """Close all connections in the pool (call on shutdown)."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Content-agent DB pool closed")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context-manager: checks out a connection and returns it when done."""
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

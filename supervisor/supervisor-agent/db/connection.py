"""
PostgreSQL connection pool for supervisor-agent.
Uses psycopg2.pool.SimpleConnectionPool — same pattern as analytics/marketing agents.
"""
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

import psycopg2
from psycopg2 import pool

import logging

logger = logging.getLogger("supervisor.db.connection")

_pool: pool.SimpleConnectionPool | None = None


def require_database_url(db_url: Optional[str] = None) -> str:
    resolved = db_url or os.environ.get("DATABASE_URL")
    if not resolved:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return resolved


def init_pool(minconn: int = 2, maxconn: int = 10) -> None:
    """Initialise the global connection pool (call once at startup)."""
    global _pool
    dsn = require_database_url()
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
    """Context-manager that checks out a connection and returns it when done."""
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


def coerce_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

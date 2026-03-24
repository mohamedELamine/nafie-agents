import os
from datetime import datetime
from typing import Optional


def require_database_url(db_url: Optional[str] = None) -> str:
    resolved = db_url or os.environ.get("DATABASE_URL")
    if not resolved:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return resolved


def connect_db(db_url: Optional[str] = None):
    import psycopg2

    conn = psycopg2.connect(require_database_url(db_url))
    conn.autocommit = False
    return conn


def ensure_connection(conn, db_url: Optional[str] = None):
    if conn is None or getattr(conn, "closed", 1):
        return connect_db(db_url)
    return conn


def coerce_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

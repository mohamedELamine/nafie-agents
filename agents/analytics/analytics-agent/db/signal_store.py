from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.signal_store")


def save_signal(conn: psycopg2.extensions.connection, signal: Dict[str, Any]) -> None:
    """Save an analytics signal."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analytics_signals (
                    signal_id, signal_type, priority, target_agent, theme_slug,
                    confidence, data, generated_at, sent_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signal_id) DO NOTHING
                """,
                (
                    signal["signal_id"],
                    signal["signal_type"],
                    signal["priority"],
                    signal["target_agent"],
                    signal["theme_slug"],
                    signal["confidence"],
                    str(signal["data"]),
                    signal["generated_at"],
                    signal.get("sent_at"),
                ),
            )
            conn.commit()
            logger.debug(f"Saved signal: {signal['signal_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving signal: {e}")


def signal_sent_recently(
    conn: psycopg2.extensions.connection,
    signal_type: str,
    theme_slug: Optional[str],
    hours: int = 24,
    filter_key: Optional[str] = None,
) -> bool:
    """Check if a signal was sent recently. theme_slug=None matches global signals."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            if theme_slug is None:
                cursor.execute(
                    """
                    SELECT 1 FROM analytics_signals
                    WHERE signal_type = %s
                    AND theme_slug IS NULL
                    AND generated_at >= %s
                    LIMIT 1
                    """,
                    (signal_type, cutoff),
                )
            else:
                cursor.execute(
                    """
                    SELECT 1 FROM analytics_signals
                    WHERE signal_type = %s
                    AND theme_slug = %s
                    AND generated_at >= %s
                    LIMIT 1
                    """,
                    (signal_type, theme_slug, cutoff),
                )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking recent signal: {e}")
        return False


def mark_signal_sent(conn: psycopg2.extensions.connection, signal_id: str) -> None:
    """Mark a signal as sent."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE analytics_signals 
                SET sent_at = %s 
                WHERE signal_id = %s
                """,
                (datetime.utcnow(), signal_id),
            )
            conn.commit()
            logger.debug(f"Marked signal as sent: {signal_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking signal as sent: {e}")


def get_signals_by_type(
    conn:         psycopg2.extensions.connection,
    signal_type:  str,
    limit:        int  = 100,
    include_sent: bool = False,
) -> List[Dict[str, Any]]:
    """Get signals of a specific type. signal_type='all' → بلا تصفية."""
    try:
        with conn.cursor() as cursor:
            if signal_type == "all":
                query  = "SELECT * FROM analytics_signals WHERE 1=1"
                params = []
            else:
                query  = "SELECT * FROM analytics_signals WHERE signal_type = %s"
                params = [signal_type]

            if not include_sent:
                query += " AND sent_at IS NULL"

            query += " ORDER BY generated_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows    = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting signals by type: {e}")
        return []


def get_signals_filtered(
    conn:         psycopg2.extensions.connection,
    signal_type:  Optional[str] = None,
    target_agent: Optional[str] = None,
    since:        Optional[datetime] = None,
    limit:        int = 100,
) -> List[Dict[str, Any]]:
    """فلترة مرنة للإشارات — للـ API."""
    try:
        with conn.cursor() as cursor:
            query  = "SELECT * FROM analytics_signals WHERE 1=1"
            params = []

            if signal_type:
                query += " AND signal_type = %s"
                params.append(signal_type)

            if target_agent:
                query += " AND target_agent = %s"
                params.append(target_agent)

            if since:
                query += " AND generated_at >= %s"
                params.append(since)

            query += " ORDER BY generated_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows    = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_signals_filtered: {e}")
        return []

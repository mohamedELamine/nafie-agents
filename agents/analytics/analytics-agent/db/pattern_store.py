from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from ..logging_config import get_logger

logger = get_logger("db.pattern_store")


def save_pattern(conn: psycopg2.extensions.connection, pattern: Dict[str, Any]) -> None:
    """Save a pattern."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analytics_patterns (
                    pattern_id, pattern_type, analytics_type, confidence,
                    supporting_metrics, detected_at, is_actionable
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pattern_id) DO NOTHING
                """,
                (
                    pattern["pattern_id"],
                    pattern["pattern_type"],
                    pattern["analytics_type"],
                    pattern["confidence"],
                    str(pattern["supporting_metrics"]),
                    pattern["detected_at"],
                    pattern.get("is_actionable", True),
                ),
            )
            conn.commit()
            logger.debug(f"Saved pattern: {pattern['pattern_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving pattern: {e}")


def get_recent_patterns(
    conn: psycopg2.extensions.connection,
    limit: int = 50,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """Get recent patterns."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            cursor.execute(
                """
                SELECT * FROM analytics_patterns 
                WHERE detected_at >= %s
                ORDER BY detected_at DESC
                LIMIT %s
                """,
                (cutoff, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting recent patterns: {e}")
        return []


def get_patterns_by_type(
    conn: psycopg2.extensions.connection,
    pattern_type: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get patterns of a specific type."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM analytics_patterns 
                WHERE pattern_type = %s
                ORDER BY detected_at DESC
                LIMIT %s
                """,
                (pattern_type, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting patterns by type: {e}")
        return []

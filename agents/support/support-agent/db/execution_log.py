from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.execution_log")


def mark_started(
    conn: psycopg2.extensions.connection,
    execution_id: str,
    ticket_id: str,
    platform: str,
) -> None:
    """Mark execution as started."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO support_execution_log (
                    execution_id, ticket_id, platform, started_at, status
                ) VALUES (%s, %s, %s, %s, 'in_progress')
                ON CONFLICT (execution_id) DO UPDATE SET
                    status = 'in_progress',
                    started_at = EXCLUDED.started_at
                """,
                (execution_id, ticket_id, platform, datetime.utcnow()),
            )
            conn.commit()
            logger.debug(f"Marked execution {execution_id} as started")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking execution as started: {e}")


def mark_completed(
    conn: psycopg2.extensions.connection,
    execution_id: str,
    ticket_id: str,
    platform: str,
    answer: Optional[str] = None,
    confidence: Optional[float] = None,
) -> None:
    """Mark execution as completed."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE support_execution_log 
                SET status = 'completed', completed_at = %s
                WHERE execution_id = %s
                """,
                (datetime.utcnow(), execution_id),
            )
            conn.commit()
            logger.debug(f"Marked execution {execution_id} as completed")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking execution as completed: {e}")


def mark_failed(
    conn: psycopg2.extensions.connection, execution_id: str, error_message: str
) -> None:
    """Mark execution as failed."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE support_execution_log 
                SET status = 'failed', completed_at = %s, error_message = %s
                WHERE execution_id = %s
                """,
                (datetime.utcnow(), error_message, execution_id),
            )
            conn.commit()
            logger.error(f"Marked execution {execution_id} as failed: {error_message}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking execution as failed: {e}")


def check_completed(
    conn: psycopg2.extensions.connection, ticket_id: str, platform: str, hours: int = 24
) -> bool:
    """Check if a ticket was already processed recently."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            cursor.execute(
                """
                SELECT COUNT(*) FROM support_execution_log
                WHERE ticket_id = %s 
                AND platform = %s
                AND completed_at >= %s
                """,
                (ticket_id, platform, cutoff),
            )
            count = cursor.fetchone()[0]
            return count > 0
    except Exception as e:
        logger.error(f"Error checking execution status: {e}")
        return False

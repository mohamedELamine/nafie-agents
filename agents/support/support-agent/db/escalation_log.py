from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.escalation_log")


def save_escalation(
    conn: psycopg2.extensions.connection, escalation: Dict[str, Any]
) -> None:
    """Save an escalation record."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO support_escalation_log (
                    escalation_id, ticket_id, ticket_platform, escalation_reason,
                    original_message, customer_identity, current_agent_context, escalation_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (escalation_id) DO UPDATE SET
                    resolution_status = EXCLUDED.resolution_status,
                    escalation_time = EXCLUDED.escalation_time
                """,
                (
                    escalation["escalation_id"],
                    escalation["ticket_id"],
                    escalation["ticket_platform"],
                    escalation["escalation_reason"],
                    escalation["original_message"],
                    str(escalation["customer_identity"]),
                    escalation["current_agent_context"],
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.info(f"Saved escalation: {escalation['escalation_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving escalation: {e}")


def get_escalation_history(
    conn: psycopg2.extensions.connection,
    ticket_id: Optional[str] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Get escalation history."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            if ticket_id:
                cursor.execute(
                    """
                    SELECT * FROM support_escalation_log 
                    WHERE ticket_id = %s
                    AND escalation_time >= %s
                    ORDER BY escalation_time DESC
                    """,
                    (ticket_id, cutoff),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM support_escalation_log 
                    WHERE escalation_time >= %s
                    ORDER BY escalation_time DESC
                    LIMIT 100
                    """,
                    (cutoff,),
                )

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting escalation history: {e}")
        return []


def get_escalations_by_reason(
    conn: psycopg2.extensions.connection, reason: str, days: int = 30
) -> List[Dict[str, Any]]:
    """Get escalations by reason."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            cursor.execute(
                """
                SELECT * FROM support_escalation_log 
                WHERE escalation_reason = %s
                AND escalation_time >= %s
                ORDER BY escalation_time DESC
                LIMIT 100
                """,
                (reason, cutoff),
            )

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting escalations by reason: {e}")
        return []

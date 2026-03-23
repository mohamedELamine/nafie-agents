from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.knowledge_log")


def save_update(conn: psycopg2.extensions.connection, update: Dict[str, Any]) -> None:
    """Save a knowledge base update."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO support_knowledge_log (
                    update_id, collection, document_id, content, metadata, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (update_id) DO NOTHING
                """,
                (
                    update["update_id"],
                    update["collection"],
                    update["document_id"],
                    update["content"],
                    str(update["metadata"]),
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.info(f"Saved knowledge update: {update['update_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving knowledge update: {e}")


def get_recent_updates(
    conn: psycopg2.extensions.connection,
    collection: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get recent knowledge base updates."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            if collection:
                cursor.execute(
                    """
                    SELECT * FROM support_knowledge_log 
                    WHERE collection = %s
                    AND created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (collection, cutoff, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM support_knowledge_log 
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (cutoff, limit),
                )

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting recent updates: {e}")
        return []

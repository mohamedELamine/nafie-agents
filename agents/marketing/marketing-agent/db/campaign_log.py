from datetime import datetime, timedelta
from typing import Any, Dict, List

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.campaign_log")


def save_log(conn: psycopg2.extensions.connection, log_entry: Dict[str, Any]) -> None:
    """Save a campaign log entry."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO campaign_log (
                    log_id, campaign_id, event_type, details, created_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (log_id) DO NOTHING
                """,
                (
                    log_entry["log_id"],
                    log_entry["campaign_id"],
                    log_entry["event_type"],
                    str(log_entry["details"]),
                    log_entry.get("created_at", datetime.utcnow()),
                ),
            )
            conn.commit()
            logger.debug(f"Saved campaign log: {log_entry['log_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving campaign log: {e}")


def get_campaign_history(
    conn: psycopg2.extensions.connection,
    campaign_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get campaign history for a specific campaign."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM campaign_log 
                WHERE campaign_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (campaign_id, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting campaign history: {e}")
        return []


def get_channel_stats(
    conn: psycopg2.extensions.connection,
    campaign_id: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get statistics for a campaign by channel."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            cursor.execute(
                """
                SELECT 
                    channel,
                    COUNT(*) as total_posts,
                    SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(scheduled_time) as avg_scheduled_time
                FROM scheduled_posts
                WHERE campaign_id = %s
                AND scheduled_time >= %s
                GROUP BY channel
                ORDER BY total_posts DESC
                """,
                (campaign_id, cutoff),
            )
            rows = cursor.fetchall()

            stats = {
                "total_posts": 0,
                "published": 0,
                "failed": 0,
                "by_channel": {},
            }

            for row in rows:
                channel_stats = {
                    "channel": row[0],
                    "total_posts": row[1],
                    "published": row[2],
                    "failed": row[3],
                    "avg_scheduled_time": row[4].isoformat() if row[4] else None,
                }
                stats["by_channel"][row[0]] = channel_stats
                stats["total_posts"] += row[1]
                stats["published"] += row[2]
                stats["failed"] += row[3]

            return stats
    except Exception as e:
        logger.error(f"Error getting channel stats: {e}")
        return {
            "total_posts": 0,
            "published": 0,
            "failed": 0,
            "by_channel": {},
        }

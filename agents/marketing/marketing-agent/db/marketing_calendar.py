from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.marketing_calendar")


def save_campaign(
    conn: psycopg2.extensions.connection, campaign: Dict[str, Any]
) -> None:
    """Save a campaign to the marketing calendar."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketing_calendar (
                    campaign_id, title, theme_slug, 
                    content_snapshot, assets_snapshot, 
                    start_date, end_date, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (campaign_id) DO NOTHING
                """,
                (
                    campaign["campaign_id"],
                    campaign["title"],
                    campaign["theme_slug"],
                    str(campaign["content_snapshot"]),
                    str(campaign["assets_snapshot"]),
                    campaign["start_date"],
                    campaign["end_date"],
                    campaign["status"],
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.debug(f"Saved campaign: {campaign['campaign_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving campaign: {e}")


def schedule_post(conn: psycopg2.extensions.connection, post: Dict[str, Any]) -> None:
    """Schedule a post in the marketing calendar."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scheduled_posts (
                    post_id, campaign_id, channel, format,
                    scheduled_time, content_snapshot_id,
                    asset_snapshot_id, status, variant_label,
                    scheduled_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (post_id) DO NOTHING
                """,
                (
                    post["post_id"],
                    post["campaign_id"],
                    post["channel"],
                    post["format"],
                    post["scheduled_time"],
                    post["content_snapshot_id"],
                    post["asset_snapshot_id"],
                    post["status"],
                    post.get("variant_label"),
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.debug(f"Scheduled post: {post['post_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error scheduling post: {e}")


def get_pending_posts(
    conn: psycopg2.extensions.connection, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get pending posts that should be published now or later."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow()

            cursor.execute(
                """
                SELECT * FROM scheduled_posts 
                WHERE status IN ('pending', 'scheduled')
                AND scheduled_time <= %s
                ORDER BY scheduled_time ASC
                LIMIT %s
                """,
                (cutoff, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting pending posts: {e}")
        return []


def mark_published(conn: psycopg2.extensions.connection, post_id: str) -> None:
    """Mark a post as published."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE scheduled_posts 
                SET status = 'published', published_at = %s 
                WHERE post_id = %s
                """,
                (datetime.utcnow(), post_id),
            )
            conn.commit()
            logger.debug(f"Marked post as published: {post_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking post as published: {e}")


def mark_failed(
    conn: psycopg2.extensions.connection, post_id: str, reason: str
) -> None:
    """Mark a post as failed."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE scheduled_posts 
                SET status = 'failed', failure_reason = %s
                WHERE post_id = %s
                """,
                (reason, post_id),
            )
            conn.commit()
            logger.debug(f"Marked post as failed: {post_id}, reason: {reason}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error marking post as failed: {e}")


def get_scheduled_posts(
    conn: psycopg2.extensions.connection,
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get scheduled posts with optional filtering."""
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM scheduled_posts WHERE 1=1"
            params = []

            if campaign_id:
                query += " AND campaign_id = %s"
                params.append(campaign_id)

            if status:
                query += " AND status = %s"
                params.append(status)

            query += " ORDER BY scheduled_time ASC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting scheduled posts: {e}")
        return []


def get_campaign_by_id(
    conn: psycopg2.extensions.connection, campaign_id: str
) -> Optional[Dict[str, Any]]:
    """Get a campaign by ID."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM marketing_calendar WHERE campaign_id = %s",
                (campaign_id,),
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        return None

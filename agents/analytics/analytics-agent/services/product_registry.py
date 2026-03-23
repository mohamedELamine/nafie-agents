from datetime import datetime
from typing import Dict, List, Optional

import psycopg2

from ..logging_config import get_logger
from .redis_bus import get_redis_bus

logger = get_logger("services.product_registry")


def get_all_published_slugs() -> List[str]:
    """Get all published product slugs from database."""
    try:
        conn = psycopg2.connect(
            "postgresql://analytics:password@localhost:5432/analytics_db"
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT theme_slug 
                FROM analytics_events 
                WHERE event_type = 'NEW_PRODUCT_LIVE'
                ORDER BY received_at DESC
            """)
            slugs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return slugs
    except Exception as e:
        logger.error(f"Error getting published slugs: {e}")
        return []


def get_launch_date(slug: str) -> Optional[datetime]:
    """Get launch date for a product."""
    try:
        conn = psycopg2.connect(
            "postgresql://analytics:password@localhost:5432/analytics_db"
        )
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT MAX(occurred_at) as launch_date
                FROM analytics_events
                WHERE theme_slug = %s
                AND event_type = 'NEW_PRODUCT_LIVE'
                LIMIT 1
            """,
                (slug,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
        conn.close()
        return None
    except Exception as e:
        logger.error(f"Error getting launch date for {slug}: {e}")
        return None


def get_product_activity_summary(slug: str, days: int = 30) -> Dict[str, any]:
    """Get activity summary for a product."""
    try:
        conn = psycopg2.connect(
            "postgresql://analytics:password@localhost:5432/analytics_db"
        )
        with conn.cursor() as cursor:
            # Get recent events
            cursor.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM analytics_events
                WHERE theme_slug = %s
                AND occurred_at >= NOW() - INTERVAL '%s days'
                GROUP BY event_type
                ORDER BY count DESC
            """,
                (slug, days),
            )
            events_by_type = {row[0]: row[1] for row in cursor.fetchall()}

            # Get revenue
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount_usd), 0) as revenue
                FROM analytics_events
                WHERE theme_slug = %s
                AND event_type = 'NEW_SALE'
                AND occurred_at >= NOW() - INTERVAL '%s days'
            """,
                (slug, days),
            )
            revenue = cursor.fetchone()[0]

            # Get support tickets
            cursor.execute(
                """
                SELECT COUNT(*) as ticket_count
                FROM analytics_events
                WHERE theme_slug = %s
                AND event_type = 'SUPPORT_TICKET_RESOLVED'
                AND occurred_at >= NOW() - INTERVAL '%s days'
            """,
                (slug, days),
            )
            tickets = cursor.fetchone()[0]

        conn.close()
        return {
            "events_by_type": events_by_type,
            "revenue": revenue,
            "support_tickets": tickets,
        }
    except Exception as e:
        logger.error(f"Error getting activity summary for {slug}: {e}")
        return {
            "events_by_type": {},
            "revenue": 0.0,
            "support_tickets": 0,
        }

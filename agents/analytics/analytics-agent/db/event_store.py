from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from ..logging_config import get_logger

logger = get_logger("db.event_store")


def save_event(conn: psycopg2.extensions.connection, event: Dict[str, Any]) -> None:
    """Save an analytics event to the database."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO analytics_events (
                    event_id, event_type, source_agent, theme_slug, raw_data,
                    occurred_at, received_at, processed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    event["event_id"],
                    event["event_type"],
                    event["source_agent"],
                    event["theme_slug"],
                    str(event["raw_data"]),
                    event["occurred_at"],
                    event["received_at"],
                    event.get("processed", False),
                ),
            )
            conn.commit()
            logger.debug(f"Saved event: {event['event_id']}")
    except psycopg2.IntegrityError:
        conn.rollback()
        logger.debug(f"Event already exists: {event['event_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving event: {e}")


def event_exists(conn: psycopg2.extensions.connection, event_id: str) -> bool:
    """Check if an event exists."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM analytics_events WHERE event_id = %s",
                (event_id,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking event existence: {e}")
        return False


def count_events(
    conn: psycopg2.extensions.connection,
    event_type: Optional[str] = None,
    theme_slug: Optional[str] = None,
    since: Optional[datetime] = None,
) -> int:
    """Count events within a time window, with optional filters."""
    try:
        with conn.cursor() as cursor:
            query  = "SELECT COUNT(*) FROM analytics_events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)

            if theme_slug is not None:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            if since:
                query += " AND occurred_at >= %s"
                params.append(since)

            cursor.execute(query, params)
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error counting events: {e}")
        return 0


def get_last_event(
    conn: psycopg2.extensions.connection,
    event_type: Optional[str] = None,
    theme_slug: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Get the most recent event, with optional filters."""
    try:
        with conn.cursor() as cursor:
            query  = "SELECT * FROM analytics_events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)

            if theme_slug is not None:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            query += " ORDER BY occurred_at DESC LIMIT 1"

            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting last event: {e}")
        return None


def get_events(
    conn: psycopg2.extensions.connection,
    event_type: Optional[str] = None,
    theme_slug: Optional[str] = None,
    since: Optional[datetime] = None,
    before: Optional[datetime] = None,
    limit: int = 1000,
    filter_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Get events with optional filtering. Uses occurred_at for time queries."""
    try:
        with conn.cursor() as cursor:
            query  = "SELECT * FROM analytics_events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)

            if theme_slug is not None:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            if since:
                query += " AND occurred_at >= %s"
                params.append(since)

            if before:
                query += " AND occurred_at < %s"
                params.append(before)

            query += " ORDER BY occurred_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]

            # تصفية بحسب raw_data إن طُلب
            if filter_data:
                import json
                filtered = []
                for r in results:
                    rd = r.get("raw_data") or {}
                    if isinstance(rd, str):
                        try:
                            rd = json.loads(rd)
                        except Exception:
                            rd = {}
                    if all(rd.get(k) == v for k, v in filter_data.items()):
                        filtered.append(r)
                return filtered

            return results
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return []


def backfill_sale(
    conn: psycopg2.extensions.connection,
    sale_id: str,
    sale_date: datetime,
    theme_slug: str,
    amount_usd: float,
    license_tier: str,
) -> None:
    """Backfill a sale event."""
    try:
        with conn.cursor() as cursor:
            event_id = f"sale_{sale_id}"

            if event_exists(conn, event_id):
                logger.debug(f"Sale event already exists: {event_id}")
                return

            event = {
                "event_id": event_id,
                "event_type": "NEW_SALE",
                "source_agent": "lemon_squeezy",
                "theme_slug": theme_slug,
                "raw_data": {
                    "sale_id": sale_id,
                    "sale_date": sale_date.isoformat(),
                    "amount_usd": amount_usd,
                    "license_tier": license_tier,
                },
                "occurred_at": sale_date,
                "received_at": datetime.utcnow(),
                "processed": False,
            }

            save_event(conn, event)
            logger.info(f"Backfilled sale event: {sale_id}")
    except Exception as e:
        logger.error(f"Error backfilling sale: {e}")


def get_events_by_type(
    conn: psycopg2.extensions.connection,
    event_type: str,
    since: Optional[datetime] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Get events of a specific type."""
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM analytics_events WHERE event_type = %s"
            params = [event_type]

            if since:
                query += " AND occurred_at >= %s"
                params.append(since)

            query += " ORDER BY received_at DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting events by type: {e}")
        return []

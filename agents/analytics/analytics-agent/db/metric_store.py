from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from ..logging_config import get_logger

logger = get_logger("db.metric_store")


def save_snapshot(
    conn: psycopg2.extensions.connection,
    metric_id:    str,
    metric_key:   str,
    theme_slug:   Optional[str],
    channel:      Optional[str],
    granularity:  str,
    period_start: datetime,
    period_end:   datetime,
    value:        float,
    unit:         str,
) -> None:
    """Save a metric snapshot — idempotent via ON CONFLICT DO NOTHING."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO metric_snapshots (
                    metric_id, metric_key, theme_slug, channel, granularity,
                    period_start, period_end, value, unit, computed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (metric_key, granularity, period_start, theme_slug, channel)
                DO NOTHING
                """,
                (
                    metric_id,
                    metric_key,
                    theme_slug,
                    channel,
                    granularity,
                    period_start,
                    period_end,
                    value,
                    unit,
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.debug(f"Saved metric snapshot: {metric_key}/{granularity}/{period_start}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving metric snapshot: {e}")


def snapshot_exists(
    conn:         psycopg2.extensions.connection,
    metric_key:   str,
    granularity:  str,
    period_start: datetime,
    theme_slug:   Optional[str] = None,
    channel:      Optional[str] = None,
) -> bool:
    """تحقق idempotency — هل تم حساب هذا المقياس لهذه الفترة؟"""
    try:
        with conn.cursor() as cursor:
            query  = """
                SELECT 1 FROM metric_snapshots
                WHERE metric_key = %s AND granularity = %s AND period_start = %s
            """
            params = [metric_key, granularity, period_start]

            if theme_slug is not None:
                query += " AND theme_slug = %s"
                params.append(theme_slug)
            else:
                query += " AND theme_slug IS NULL"

            if channel is not None:
                query += " AND channel = %s"
                params.append(channel)
            else:
                query += " AND channel IS NULL"

            query += " LIMIT 1"
            cursor.execute(query, params)
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking snapshot existence: {e}")
        return False


def sum_snapshots(
    conn:         psycopg2.extensions.connection,
    metric_key:   str,
    granularity:  str,
    period_start: datetime,
    period_end:   datetime,
    theme_slug:   Optional[str] = None,
    channel:      Optional[str] = None,
) -> float:
    """يجمع قيم snapshots في نافذة زمنية (للـ aggregation)."""
    try:
        with conn.cursor() as cursor:
            query  = """
                SELECT COALESCE(SUM(value), 0)
                FROM metric_snapshots
                WHERE metric_key = %s AND granularity = %s
                AND period_start >= %s AND period_start < %s
            """
            params = [metric_key, granularity, period_start, period_end]

            if theme_slug is not None:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            if channel is not None:
                query += " AND channel = %s"
                params.append(channel)

            cursor.execute(query, params)
            return float(cursor.fetchone()[0])
    except Exception as e:
        logger.error(f"Error summing snapshots: {e}")
        return 0.0


def get_snapshots_by_key(
    conn:         psycopg2.extensions.connection,
    metric_key:   str,
    granularity:  str,
    period_start: datetime,
    period_end:   datetime,
) -> List[Dict[str, Any]]:
    """يُعيد كل snapshots لمقياس محدد في فترة زمنية."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM metric_snapshots
                WHERE metric_key = %s AND granularity = %s
                AND period_start >= %s AND period_start < %s
                ORDER BY period_start
                """,
                (metric_key, granularity, period_start, period_end),
            )
            rows    = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting snapshots by key: {e}")
        return []


def get_snapshot(
    conn: psycopg2.extensions.connection,
    metric_key: str,
    period_start: datetime,
    period_end: datetime,
    theme_slug: Optional[str] = None,
    channel: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Get a metric snapshot."""
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT * FROM metric_snapshots 
                WHERE metric_key = %s AND period_start = %s AND period_end = %s
            """
            params = [metric_key, period_start, period_end]

            if theme_slug:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            if channel:
                query += " AND channel = %s"
                params.append(channel)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting metric snapshot: {e}")
        return None


def sum_metrics(
    conn: psycopg2.extensions.connection,
    metric_keys: List[str],
    period_start: datetime,
    period_end: datetime,
    theme_slug: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, float]:
    """Sum values for multiple metrics."""
    try:
        with conn.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(metric_keys))
            query = f"""
                SELECT metric_key, SUM(value) as total
                FROM metric_snapshots 
                WHERE metric_key IN ({placeholders})
                AND period_start = %s AND period_end = %s
            """
            params = [*metric_keys, period_start, period_end]

            if theme_slug:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            if channel:
                query += " AND channel = %s"
                params.append(channel)

            query += " GROUP BY metric_key"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = {row[0]: row[1] for row in rows}
            # Fill in missing metrics with 0
            for key in metric_keys:
                if key not in result:
                    result[key] = 0.0

            return result
    except Exception as e:
        logger.error(f"Error summing metrics: {e}")
        return {key: 0.0 for key in metric_keys}


def aggregate_hourly_to_daily(
    conn: psycopg2.extensions.connection,
    metric_key: str,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """Aggregate hourly metrics to daily."""
    try:
        with conn.cursor() as cursor:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            query = """
                SELECT 
                    DATE_TRUNC('day', period_start) as day,
                    SUM(value) as total
                FROM metric_snapshots
                WHERE metric_key = %s
                AND period_start >= %s
                AND granularity = 'hour'
                AND period_end >= %s
                GROUP BY day
                ORDER BY day DESC
            """
            cursor.execute(query, (metric_key, start_date, start_date))
            rows = cursor.fetchall()

            result = [{"date": row[0].isoformat(), "value": row[1]} for row in rows]
            return result
    except Exception as e:
        logger.error(f"Error aggregating hourly to daily: {e}")
        return []


def get_period_metrics(
    conn: psycopg2.extensions.connection,
    period_start: datetime,
    period_end: datetime,
    theme_slug: Optional[str] = None,
    granularity: str = "day",
) -> List[Dict[str, Any]]:
    """Get metrics for a specific period."""
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT * FROM metric_snapshots 
                WHERE period_start >= %s 
                AND period_end <= %s
                AND granularity = %s
            """
            params = [period_start, period_end, granularity]

            if theme_slug:
                query += " AND theme_slug = %s"
                params.append(theme_slug)

            query += " ORDER BY period_start DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting period metrics: {e}")
        return []

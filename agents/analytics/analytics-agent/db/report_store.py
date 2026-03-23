from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from ..logging_config import get_logger

logger = get_logger("db.report_store")


def save_report(conn: psycopg2.extensions.connection, report: Dict[str, Any]) -> None:
    """Save a weekly/monthly report."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO weekly_reports (
                    report_id, period_start, period_end, total_sales,
                    total_revenue, highlights, concerns, generated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (report_id) DO UPDATE SET
                    total_sales = EXCLUDED.total_sales,
                    total_revenue = EXCLUDED.total_revenue,
                    highlights = EXCLUDED.highlights,
                    concerns = EXCLUDED.concerns,
                    generated_at = EXCLUDED.generated_at
                """,
                (
                    report["report_id"],
                    report["period_start"],
                    report["period_end"],
                    report["total_sales"],
                    report["total_revenue"],
                    str(report["highlights"]),
                    str(report["concerns"]),
                    datetime.utcnow(),
                ),
            )
            conn.commit()
            logger.debug(f"Saved report: {report['report_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving report: {e}")


def get_report(
    conn: psycopg2.extensions.connection,
    report_id: str,
) -> Optional[Dict[str, Any]]:
    """Get a report by ID."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM weekly_reports WHERE report_id = %s",
                (report_id,),
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        return None


def get_latest_report(
    conn: psycopg2.extensions.connection,
) -> Optional[Dict[str, Any]]:
    """Get the most recent report."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM weekly_reports ORDER BY generated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting latest report: {e}")
        return None

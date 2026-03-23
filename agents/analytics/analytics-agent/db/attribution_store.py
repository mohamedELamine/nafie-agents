from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from ..logging_config import get_logger

logger = get_logger("db.attribution_store")


def save_record(conn: psycopg2.extensions.connection, record) -> None:
    """
    يحفظ AttributionRecord dataclass — الواجهة الرئيسية.
    يعتمد على occurred_at (sale_date) لا received_at.
    """
    import json
    from dataclasses import asdict

    try:
        if hasattr(record, "__dataclass_fields__"):
            data = asdict(record)
        else:
            data = record

        channels = [
            ch.value if hasattr(ch, "value") else str(ch)
            for ch in (data.get("channels_touched") or [])
        ]
        attributed = (
            data["attributed_to"].value
            if hasattr(data.get("attributed_to"), "value")
            else str(data.get("attributed_to", "unknown"))
        )
        confidence = (
            data["attribution_confidence"].value
            if hasattr(data.get("attribution_confidence"), "value")
            else str(data.get("attribution_confidence", "low"))
        )

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO attribution_records (
                    sale_id, theme_slug, amount_usd, license_tier,
                    channels_touched, attributed_to, attribution_model,
                    attribution_confidence, attribution_note, sale_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sale_id) DO NOTHING
                """,
                (
                    data["sale_id"],
                    data["theme_slug"],
                    float(data.get("amount_usd", 0)),
                    data.get("license_tier", "unknown"),
                    json.dumps(channels),
                    attributed,
                    data.get("attribution_model", "last_touch_v1"),
                    confidence,
                    data.get("attribution_note", ""),
                    data["sale_date"],
                ),
            )
            conn.commit()
            logger.debug(f"Saved attribution: {data['sale_id']} → {attributed} [{confidence}]")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving attribution record: {e}")


def save_attribution_record(
    conn: psycopg2.extensions.connection,
    sale_id: str,
    theme_slug: str,
    attributed_to: str,
    confidence: str,
    channels_touched: List[str],
    attribution_note: Optional[str] = None,
    sale_date: Optional[datetime] = None,
) -> None:
    """Legacy interface — يُفضَّل استخدام save_record()."""
    import json
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO attribution_records (
                    sale_id, theme_slug, amount_usd, license_tier,
                    channels_touched, attributed_to, attribution_model,
                    attribution_confidence, attribution_note, sale_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sale_id) DO NOTHING
                """,
                (
                    sale_id, theme_slug, 0, "unknown",
                    json.dumps(channels_touched), attributed_to, "last_touch_v1",
                    confidence, attribution_note or "", sale_date,
                ),
            )
            conn.commit()
            logger.debug(f"Saved attribution: {sale_id} → {attributed_to}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving attribution record: {e}")


def get_records_by_theme(
    conn: psycopg2.extensions.connection,
    theme_slug: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get attribution records for a theme."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM attribution_records 
                WHERE theme_slug = %s 
                ORDER BY sale_date DESC 
                LIMIT %s
                """,
                (theme_slug, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting records by theme: {e}")
        return []


def get_records_by_channel(
    conn: psycopg2.extensions.connection,
    channel: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get attribution records for a channel."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM attribution_records 
                WHERE channels_touched::text LIKE %s 
                ORDER BY sale_date DESC 
                LIMIT %s
                """,
                (f"%{channel}%", limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting records by channel: {e}")
        return []


def get_attribution_summary(
    conn: psycopg2.extensions.connection,
    days: int = 7,
) -> Dict[str, Any]:
    """Get attribution summary for recent period."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            cursor.execute(
                """
                SELECT 
                    attributed_to,
                    COUNT(*) as sale_count,
                    SUM(1.0) as revenue
                FROM attribution_records
                WHERE sale_date >= %s
                GROUP BY attributed_to
                ORDER BY sale_count DESC
                """,
                (cutoff,),
            )
            rows = cursor.fetchall()

            summary = {
                "total_sales": len(rows),
                "total_revenue": sum(row[2] for row in rows),
                "by_attribution": [
                    {
                        "attributed_to": row[0],
                        "sale_count": row[1],
                        "revenue": row[2],
                    }
                    for row in rows
                ],
            }
            return summary
    except Exception as e:
        logger.error(f"Error getting attribution summary: {e}")
        return {
            "total_sales": 0,
            "total_revenue": 0.0,
            "by_attribution": [],
        }

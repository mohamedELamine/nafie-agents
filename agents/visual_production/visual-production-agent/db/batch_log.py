"""
Batch log DB operations — psycopg2 + get_conn().
All writes use ON CONFLICT DO NOTHING (Constitutional Law III).
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional


logger = logging.getLogger("visual_production.db.batch_log")


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def save_batch(conn, batch_data: Dict[str, Any]) -> str:
    """Upsert batch log entry. Returns batch_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO batch_log (
                batch_id, theme_slug, started_at, budget_used,
                assets_count, status, generated_assets,
                quality_approved, quality_rejected
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (batch_id) DO NOTHING
            """,
            (
                batch_data["batch_id"],
                batch_data["theme_slug"],
                batch_data.get("started_at", datetime.utcnow()),
                batch_data.get("budget_used", 0.0),
                batch_data.get("assets_count", 0),
                batch_data.get("status", "pending"),
                batch_data.get("generated_assets", 0),
                batch_data.get("quality_approved", 0),
                batch_data.get("quality_rejected", 0),
            ),
        )
    logger.info(f"Upserted batch log for {batch_data['batch_id']}")
    return batch_data["batch_id"]


def mark_completed(conn, batch_id: str, error_message: Optional[str] = None) -> None:
    """Mark batch as completed (or failed)."""
    status = "failed" if error_message else "completed"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE batch_log
            SET status = %s, completed_at = NOW(), error_message = %s
            WHERE batch_id = %s
            """,
            (status, error_message, batch_id),
        )
    logger.info(f"Batch {batch_id} marked {status}")


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_batch(conn, batch_id: str) -> Optional[Dict[str, Any]]:
    """Fetch batch log by batch_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT batch_id, theme_slug, started_at, budget_used,
                   assets_count, status, generated_assets,
                   quality_approved, quality_rejected,
                   completed_at, error_message
            FROM batch_log
            WHERE batch_id = %s
            """,
            (batch_id,),
        )
        row = cur.fetchone()

    if not row:
        return None

    return {
        "batch_id": row[0],
        "theme_slug": row[1],
        "started_at": row[2].isoformat() if row[2] else None,
        "budget_used": row[3],
        "assets_count": row[4],
        "status": row[5],
        "generated_assets": row[6],
        "quality_approved": row[7],
        "quality_rejected": row[8],
        "completed_at": row[9].isoformat() if row[9] else None,
        "error_message": row[10],
    }

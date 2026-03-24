from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2

from ..logging_config import get_logger

logger = get_logger("db.outcome_store")


def save_outcome(conn: psycopg2.extensions.connection, outcome) -> None:
    """Save a signal outcome. يقبل SignalOutcome dataclass أو dict."""
    try:
        # تحويل dataclass إلى dict إن لزم
        if hasattr(outcome, "__dataclass_fields__"):
            from dataclasses import asdict
            data = asdict(outcome)
        else:
            data = outcome

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO signal_outcomes (
                    outcome_id, signal_id, target_agent, action_taken,
                    observed_metric, before_value, after_value,
                    outcome_window_days, success_score, evaluated_at, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (outcome_id) DO NOTHING
                """,
                (
                    data["outcome_id"],
                    data["signal_id"],
                    data.get("target_agent", ""),
                    data.get("action_taken"),
                    data.get("observed_metric"),
                    data.get("before_value"),
                    data.get("after_value"),
                    data.get("outcome_window_days", 7),
                    data.get("success_score"),
                    data.get("evaluated_at") or datetime.utcnow(),
                    data.get("notes"),
                ),
            )
            conn.commit()
            logger.debug(f"Saved outcome: {data['outcome_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving outcome: {e}")


def get_outcome(
    conn: psycopg2.extensions.connection, outcome_id: str
) -> Optional[Dict[str, Any]]:
    """Get an outcome by ID."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM signal_outcomes WHERE outcome_id = %s",
                (outcome_id,),
            )
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
    except Exception as e:
        logger.error(f"Error getting outcome: {e}")
        return None


def get_outcomes_by_signal(
    conn: psycopg2.extensions.connection, signal_id: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get outcomes for a signal."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM signal_outcomes 
                WHERE signal_id = %s 
                ORDER BY evaluated_at DESC
                LIMIT %s
                """,
                (signal_id, limit),
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error getting outcomes by signal: {e}")
        return []


def get_signal_outcome_summary(
    conn: psycopg2.extensions.connection, days: int = 30
) -> Dict[str, Any]:
    """Get summary of signal outcomes."""
    try:
        with conn.cursor() as cursor:
            cutoff = datetime.utcnow() - timedelta(days=days)

            cursor.execute(
                """
                SELECT 
                    success_score,
                    COUNT(*) as count,
                    AVG(success_score) as avg_score
                FROM signal_outcomes
                WHERE evaluated_at >= %s
                GROUP BY success_score
                ORDER BY success_score DESC
                """,
                (cutoff,),
            )
            rows = cursor.fetchall()

            summary = {
                "by_score": [
                    {"success_score": row[0], "count": row[1], "avg_score": row[2]}
                    for row in rows
                ],
                "total_outcomes": sum(row[1] for row in rows),
            }
            return summary
    except Exception as e:
        logger.error(f"Error getting signal outcome summary: {e}")
        return {
            "by_score": [],
            "total_outcomes": 0,
        }

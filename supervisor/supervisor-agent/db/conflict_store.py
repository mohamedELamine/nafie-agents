import logging
import os
from typing import Optional
from datetime import datetime
from models import ConflictRecord, ConflictType
from db.connection import coerce_datetime, ensure_connection

logger = logging.getLogger("supervisor.conflict_store")


class ConflictStore:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self.conn = None

    def _connect(self):
        """Initialize database connection"""
        self.conn = ensure_connection(self.conn, self.db_url)

    def save_conflict(self, conflict: ConflictRecord) -> ConflictRecord:
        """Save conflict record"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO conflict_records
                    (conflict_id, conflict_type, agents_involved, description,
                     resolution, resolved_at, escalated, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (conflict_id) DO UPDATE SET
                        resolution = EXCLUDED.resolution,
                        resolved_at = EXCLUDED.resolved_at
                    RETURNING conflict_id
                """,
                    (
                        conflict.conflict_id,
                        conflict.conflict_type.value,
                        str(conflict.agents_involved),
                        conflict.description,
                        conflict.resolution,
                        conflict.resolved_at,
                        conflict.escalated,
                        datetime.utcnow().isoformat(),
                    ),
                )

                self.conn.commit()
                logger.info(f"Saved conflict {conflict.conflict_id}")

            return conflict

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving conflict: {e}")
            raise

    def get_open_conflicts(self) -> list[ConflictRecord]:
        """Get all open conflicts"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM conflict_records
                    WHERE resolution IS NULL
                    ORDER BY created_at DESC
                """)

                rows = cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting open conflicts: {e}")
            raise

    def resolve_conflict(
        self, conflict_id: str, resolution: str, details: Optional[dict] = None
    ) -> bool:
        """Resolve a conflict"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE conflict_records
                    SET resolution = %s, resolved_at = %s
                    WHERE conflict_id = %s
                """,
                    (resolution, datetime.utcnow().isoformat(), conflict_id),
                )

                self.conn.commit()
                logger.info(f"Resolved conflict {conflict_id}")

            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error resolving conflict: {e}")
            raise

    def get_conflict_history(self, conflict_id: str) -> list[dict]:
        """Get conflict history"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM conflict_records
                    WHERE conflict_id = %s
                    ORDER BY created_at
                """,
                    (conflict_id,),
                )

                rows = cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting conflict history: {e}")
            raise

    def _row_to_conflict(self, row) -> ConflictRecord:
        """Convert database row to ConflictRecord"""

        return ConflictRecord(
            conflict_id=row[0],
            conflict_type=ConflictType(row[1]),
            agents_involved=row[2],
            description=row[3],
            resolution=row[4],
            resolved_at=coerce_datetime(row[5]),
            escalated=row[6],
            created_at=coerce_datetime(row[7]),
        )


conflict_store = ConflictStore(db_url=os.environ.get("DATABASE_URL"))

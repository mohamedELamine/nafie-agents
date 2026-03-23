import logging
from typing import Optional
from datetime import datetime
import uuid
from models import SupervisorAuditLog, AuditCategory, EventEnvelope

logger = logging.getLogger("supervisor.audit_store")


class AuditStore:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self._connect()

    def _connect(self):
        """Initialize database connection"""
        try:
            import psycopg2

            self.conn = psycopg2.connect(self.db_url)
            self.conn.autocommit = False
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def write_audit(
        self,
        category: AuditCategory,
        action: str,
        target: str,
        workflow_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[dict] = None,
        outcome: str = "",
    ) -> str:
        """Write audit log entry - never delete"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO supervisor_audit_log
                    (log_id, category, action, target, workflow_id, correlation_id,
                     details, outcome, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING log_id
                """,
                    (
                        str(uuid.uuid4()),
                        category.value,
                        action,
                        target,
                        workflow_id,
                        correlation_id,
                        str(details) if details else None,
                        outcome,
                        datetime.utcnow().isoformat(),
                    ),
                )

                self.conn.commit()
                log_id = cursor.fetchone()[0]

                logger.info(f"Audit logged: {category.value} - {action}")

                return log_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error writing audit: {e}")
            raise

    def get_audit_log(
        self, category: Optional[AuditCategory] = None, since: Optional[datetime] = None
    ) -> list[SupervisorAuditLog]:
        """Get audit log with optional filtering"""
        try:
            with self.conn.cursor() as cursor:
                if category and since:
                    cursor.execute(
                        """
                        SELECT * FROM supervisor_audit_log
                        WHERE category = %s AND created_at >= %s
                        ORDER BY created_at DESC
                    """,
                        (category.value, since.isoformat()),
                    )
                elif category:
                    cursor.execute(
                        """
                        SELECT * FROM supervisor_audit_log
                        WHERE category = %s
                        ORDER BY created_at DESC
                    """,
                        (category.value,),
                    )
                elif since:
                    cursor.execute(
                        """
                        SELECT * FROM supervisor_audit_log
                        WHERE created_at >= %s
                        ORDER BY created_at DESC
                    """,
                        (since.isoformat(),),
                    )
                else:
                    cursor.execute("""
                        SELECT * FROM supervisor_audit_log
                        ORDER BY created_at DESC
                    """)

                rows = cursor.fetchall()
                return [self._row_to_audit(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            raise

    def _row_to_audit(self, row) -> SupervisorAuditLog:
        """Convert database row to SupervisorAuditLog"""
        from datetime import datetime

        return SupervisorAuditLog(
            log_id=row[0],
            category=AuditCategory(row[1]),
            action=row[2],
            target=row[3],
            workflow_id=row[4],
            correlation_id=row[5],
            details=row[6],
            outcome=row[7],
            created_at=datetime.fromisoformat(row[8]) if row[8] else None,
        )


audit_store = AuditStore(db_url="")

import logging
import os
from typing import Optional
from datetime import datetime, timezone
from models import WorkflowInstance, WorkflowStatus, WorkflowStep, WorkflowType
from db.connection import coerce_datetime, ensure_connection

logger = logging.getLogger("supervisor.workflow_store")


class WorkflowStore:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self.conn = None

    def _connect(self):
        """Initialize database connection"""
        self.conn = ensure_connection(self.conn, self.db_url)

    def save(self, instance: WorkflowInstance) -> WorkflowInstance:
        """Save workflow instance to database"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_instances
                    (instance_id, workflow_type, business_key, theme_slug, correlation_id,
                     current_step, total_steps, status, started_at, retry_count, context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (instance_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        current_step = EXCLUDED.current_step,
                        retry_count = EXCLUDED.retry_count
                    RETURNING instance_id, created_at
                """,
                    (
                        instance.instance_id,
                        instance.workflow_type.value,
                        instance.business_key,
                        instance.theme_slug,
                        instance.correlation_id,
                        instance.current_step,
                        instance.total_steps,
                        instance.status.value,
                        datetime.now(timezone.utc).isoformat(),
                        instance.retry_count,
                        str(instance.context) if instance.context else None,
                    ),
                )

                self.conn.commit()
                logger.info(f"Saved workflow {instance.instance_id}")

            return instance

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving workflow: {e}")
            raise

    def get(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get workflow instance by ID"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM workflow_instances WHERE instance_id = %s
                """,
                    (instance_id,),
                )

                row = cursor.fetchone()
                if row:
                    return self._row_to_instance(row)

            return None

        except Exception as e:
            logger.error(f"Error getting workflow: {e}")
            raise

    def get_by_business_key(self, business_key: str) -> Optional[WorkflowInstance]:
        """Get workflow by business key"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM workflow_instances
                    WHERE business_key = %s
                    ORDER BY started_at DESC
                    LIMIT 1
                """,
                    (business_key,),
                )

                row = cursor.fetchone()
                if row:
                    return self._row_to_instance(row)

            return None

        except Exception as e:
            logger.error(f"Error getting workflow by business key: {e}")
            raise

    def get_active_workflows(
        self, status: Optional[WorkflowStatus] = None
    ) -> list[WorkflowInstance]:
        """Get all active workflows"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                if status:
                    cursor.execute("""
                        SELECT * FROM workflow_instances
                        WHERE status IN ('RUNNING', 'WAITING')
                        ORDER BY started_at DESC
                    """)
                else:
                    cursor.execute("""
                        SELECT * FROM workflow_instances
                        WHERE status IN ('RUNNING', 'WAITING')
                        ORDER BY started_at DESC
                    """)

                rows = cursor.fetchall()
                return [self._row_to_instance(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting active workflows: {e}")
            raise

    def list_by_status(self, status: WorkflowStatus) -> list[WorkflowInstance]:
        """List workflows by status"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM workflow_instances
                    WHERE status = %s
                    ORDER BY started_at DESC
                """,
                    (status.value,),
                )

                rows = cursor.fetchall()
                return [self._row_to_instance(row) for row in rows]

        except Exception as e:
            logger.error(f"Error listing workflows by status: {e}")
            raise

    def update_step(self, instance_id: str, step: WorkflowStep) -> bool:
        """Update workflow step"""
        try:
            self._connect()
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflow_step_history
                    (instance_id, step_number, agent_name, action, status, started_at, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        instance_id,
                        step.step_number,
                        step.agent_name,
                        step.action,
                        step.status.value,
                        step.started_at,
                        step.completed_at,
                    ),
                )

                self.conn.commit()
                logger.info(f"Updated step {step.step_number} for workflow {instance_id}")

            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating step: {e}")
            raise

    def _row_to_instance(self, row) -> WorkflowInstance:
        """Convert database row to WorkflowInstance"""

        return WorkflowInstance(
            instance_id=row[0],
            workflow_type=WorkflowType(row[1]),
            business_key=row[2],
            theme_slug=row[3],
            correlation_id=row[4],
            current_step=row[5],
            total_steps=row[6],
            status=WorkflowStatus(row[7]),
            started_at=coerce_datetime(row[8]),
            completed_at=coerce_datetime(row[9]),
            failed_step=row[10],
            failure_reason=row[11],
            retry_count=row[12],
            context=row[13],
            step_history=[],
        )


workflow_store = WorkflowStore(db_url=os.environ.get("DATABASE_URL"))

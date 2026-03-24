import logging
from typing import Optional
from datetime import datetime, timezone
from models import AgentHealthRecord, AgentHealthStatus
from db.connection import coerce_datetime, get_conn

logger = logging.getLogger("supervisor.health_store")


class HealthStore:
    def save_health_record(
        self, agent_name: str, health_record: AgentHealthRecord
    ) -> AgentHealthRecord:
        """Save health record for agent"""
        try:
            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO agent_health
                        (agent_name, status, last_heartbeat, queue_depth, active_jobs,
                         error_rate, mode, last_checked, issues)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (agent_name) DO UPDATE SET
                            status = EXCLUDED.status,
                            last_heartbeat = EXCLUDED.last_heartbeat,
                            queue_depth = EXCLUDED.queue_depth,
                            active_jobs = EXCLUDED.active_jobs,
                            error_rate = EXCLUDED.error_rate,
                            mode = EXCLUDED.mode,
                            last_checked = EXCLUDED.last_checked,
                            issues = EXCLUDED.issues
                        RETURNING agent_name
                    """,
                        (
                            agent_name,
                            health_record.status.value,
                            health_record.last_heartbeat,
                            health_record.queue_depth,
                            health_record.active_jobs,
                            health_record.error_rate,
                            health_record.mode,
                            datetime.now(timezone.utc).isoformat(),
                            str(health_record.issues) if health_record.issues else None,
                        ),
                    )
                    conn.commit()
                    logger.info(f"Saved health record for {agent_name}")
            return health_record

        except Exception as e:
            logger.error(f"Error saving health record: {e}")
            raise

    def get_health(self, agent_name: str) -> Optional[AgentHealthRecord]:
        """Get health record for agent"""
        try:
            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM agent_health WHERE agent_name = %s
                    """,
                        (agent_name,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return self._row_to_health(row)
            return None

        except Exception as e:
            logger.error(f"Error getting health: {e}")
            raise

    def get_all_health(self) -> dict[str, AgentHealthRecord]:
        """Get health for all agents"""
        try:
            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM agent_health
                    """)
                    rows = cursor.fetchall()
                    return {row[0]: self._row_to_health(row) for row in rows}

        except Exception as e:
            logger.error(f"Error getting all health: {e}")
            raise

    def get_unhealthy_agents(self) -> list[str]:
        """Get all unhealthy agents"""
        try:
            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT agent_name FROM agent_health
                        WHERE status IN ('DEGRADED', 'UNHEALTHY', 'UNKNOWN')
                    """)
                    rows = cursor.fetchall()
                    return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Error getting unhealthy agents: {e}")
            raise

    def _row_to_health(self, row) -> AgentHealthRecord:
        """Convert database row to AgentHealthRecord"""
        return AgentHealthRecord(
            agent_name=row[0],
            status=AgentHealthStatus(row[1]),
            last_heartbeat=coerce_datetime(row[2]),
            queue_depth=row[3],
            active_jobs=row[4],
            error_rate=row[5],
            mode=row[6],
            last_checked=coerce_datetime(row[7]),
            issues=row[8],
        )


health_store = HealthStore()

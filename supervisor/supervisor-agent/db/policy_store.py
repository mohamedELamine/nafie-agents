import logging
from typing import Optional
from datetime import datetime
import uuid
from models import PolicyRule

logger = logging.getLogger("supervisor.policy_store")


class PolicyStore:
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

    def save_policy(self, policy: PolicyRule) -> PolicyRule:
        """Save policy rule"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO policy_rules
                    (policy_id, rule_type, condition, action, value, active,
                     created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (policy_id) DO UPDATE SET
                        condition = EXCLUDED.condition,
                        action = EXCLUDED.action,
                        value = EXCLUDED.value,
                        active = EXCLUDED.active,
                        expires_at = EXCLUDED.expires_at
                    RETURNING policy_id
                """,
                    (
                        policy.policy_id,
                        policy.rule_type,
                        str(policy.condition),
                        policy.action,
                        policy.value,
                        policy.active,
                        datetime.utcnow().isoformat(),
                        policy.expires_at,
                    ),
                )

                self.conn.commit()
                logger.info(f"Saved policy {policy.policy_id}")

            return policy

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving policy: {e}")
            raise

    def get_active_policies(self) -> list[PolicyRule]:
        """Get all active policies"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM policy_rules
                    WHERE active = TRUE
                """)

                rows = cursor.fetchall()
                return [self._row_to_policy(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting active policies: {e}")
            raise

    def deactivate_policy(self, policy_id: str) -> bool:
        """Deactivate a policy"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE policy_rules
                    SET active = FALSE
                    WHERE policy_id = %s
                """,
                    (policy_id,),
                )

                self.conn.commit()
                logger.info(f"Deactivated policy {policy_id}")

            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deactivating policy: {e}")
            raise

    def get_policy_history(self, policy_id: str) -> list[dict]:
        """Get policy history"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM policy_rules
                    WHERE policy_id = %s
                    ORDER BY created_at
                """,
                    (policy_id,),
                )

                rows = cursor.fetchall()
                return [self._row_to_policy(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting policy history: {e}")
            raise

    def _row_to_policy(self, row) -> PolicyRule:
        """Convert database row to PolicyRule"""
        from datetime import datetime

        return PolicyRule(
            policy_id=row[0],
            rule_type=row[1],
            condition=row[2],
            action=row[3],
            value=row[4],
            active=row[5],
            created_at=datetime.fromisoformat(row[6]) if row[6] else None,
            expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
        )


policy_store = PolicyStore(db_url="")

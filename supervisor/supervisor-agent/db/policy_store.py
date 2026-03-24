import logging
import os
from typing import Optional
from datetime import datetime
from models import PolicyRule
from db.connection import coerce_datetime, ensure_connection

logger = logging.getLogger("supervisor.policy_store")


class PolicyStore:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self.conn = None

    def _connect(self):
        """Initialize database connection"""
        self.conn = ensure_connection(self.conn, self.db_url)

    def save_policy(self, policy: PolicyRule) -> PolicyRule:
        """Save policy rule"""
        try:
            self._connect()
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
            self._connect()
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
            self._connect()
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
            self._connect()
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

        return PolicyRule(
            policy_id=row[0],
            rule_type=row[1],
            condition=row[2],
            action=row[3],
            value=row[4],
            active=row[5],
            created_at=coerce_datetime(row[6]),
            expires_at=coerce_datetime(row[7]),
        )


policy_store = PolicyStore(db_url=os.environ.get("DATABASE_URL"))

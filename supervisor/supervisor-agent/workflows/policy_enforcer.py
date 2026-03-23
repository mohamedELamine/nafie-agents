import logging
from typing import Dict, Any, List
from datetime import datetime
from models import AgentHealthStatus
from db.health_store import health_store
from db.audit_store import audit_store
from db.policy_store import policy_store
from policy_engine import apply_budget_action, block_launch_if_quality_fails

logger = logging.getLogger("supervisor.policy_enforcer")


class PolicyEnforcer:
    def __init__(self, audit_store):
        self.audit_store = audit_store

    async def check_and_enforce(self, context: Dict[str, Any]) -> List[str]:
        """Check and enforce policies for workflow start"""
        try:
            violations = []

            # Check daily visual budget
            if "daily_visual_budget" in context:
                current_budget = context.get("daily_visual_cost", 0)
                budget_limit = context.get("daily_visual_budget", 10.00)

                if current_budget > budget_limit:
                    action = apply_budget_action(context.get("policy", {}), current_budget)
                    violations.append(f"BUDGET_EXCEEDED: {action}")
                    logger.warning(f"Budget exceeded: {current_budget:.2f} / {budget_limit:.2f}")

            # Check daily theme limit
            if "daily_theme_limit" in context:
                theme_count = context.get("theme_count", 0)
                theme_limit = context.get("daily_theme_limit", 3)

                if theme_count >= theme_limit:
                    violations.append(f"THEME_LIMIT_EXCEEDED: {theme_count} / {theme_limit}")
                    logger.warning(f"Theme limit reached: {theme_count} / {theme_limit}")

            # Check API cost threshold
            if "api_cost_critical" in context:
                total_cost = context.get("total_api_cost", 0)
                cost_threshold = context.get("api_cost_threshold", 100.0)

                if total_cost > cost_threshold:
                    violations.append(f"API_COST_CRITICAL: {total_cost:.2f} / {cost_threshold:.2f}")
                    logger.warning(f"API cost critical: {total_cost:.2f} / {cost_threshold:.2f}")

            # Check quality threshold
            if "quality_threshold" in context:
                quality_score = context.get("quality_score", 0)
                quality_threshold = context.get("quality_threshold", 0.70)

                if quality_score < quality_threshold:
                    violations.append(
                        f"QUALITY_BELOW_THRESHOLD: {quality_score:.2f} / {quality_threshold:.2f}"
                    )
                    logger.warning(
                        f"Quality below threshold: {quality_score:.2f} / {quality_threshold:.2f}"
                    )

            # Log policy violations
            if violations:
                self.audit_store.write_audit(
                    category=AuditCategory.POLICY,
                    action="policy_violations_detected",
                    target="workflow_start",
                    details={"violations": violations},
                    outcome="warning",
                )

            return violations

        except Exception as e:
            logger.error(f"Error checking and enforcing policies: {e}")
            raise

    def apply_budget_action(self, policy: Dict[str, Any], current_cost: float) -> str:
        """Apply budget-related policy actions"""
        try:
            action = policy.get("action", "pause")

            if action == "pause_visual_production":
                return "pause_visual_production"
            elif action == "alert_and_pause":
                return "alert_and_pause"
            elif action == "block_all_budget_requests":
                return "block_all"
            else:
                return "none"

        except Exception as e:
            logger.error(f"Error applying budget action: {e}")
            return "none"

    def block_launch_if_quality_fails(self, theme_score: float) -> bool:
        """Block theme launch if quality score is below threshold"""
        try:
            quality_threshold = 0.70  # Default from constitution

            if theme_score < quality_threshold:
                logger.error(
                    f"Theme launch blocked: quality score {theme_score:.2f} < {quality_threshold:.2f}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error blocking launch based on quality: {e}")
            return False

    async def log_policy_enforcement(self, policy_id: str, action: str, outcome: str):
        """Log policy enforcement action"""
        try:
            from models import PolicyRule
            from datetime import datetime

            policy = PolicyRule(
                policy_id=policy_id,
                rule_type="enforcement",
                condition={},
                action=action,
                value=None,
                active=True,
                created_at=datetime.utcnow().isoformat(),
            )

            policy_store.save_policy(policy)

            self.audit_store.write_audit(
                category=AuditCategory.POLICY,
                action=f"policy_{action}",
                target=f"policy_{policy_id}",
                details={"outcome": outcome},
                outcome=outcome,
            )

            logger.info(f"Logged policy enforcement: {policy_id} - {action}")

        except Exception as e:
            logger.error(f"Error logging policy enforcement: {e}")


policy_enforcer = PolicyEnforcer(audit_store=audit_store)

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from models import ConflictType, ConflictRecord, SupervisorAuditLog, AuditCategory
from db.conflict_store import conflict_store
from db.audit_store import audit_store
from redis_bus import redis_bus

logger = logging.getLogger("supervisor.conflict_resolver")


class ConflictResolver:
    def __init__(self, resend_client):
        self.resend = resend_client

    def detect_conflict(self, event: Dict[str, Any]) -> Optional[ConflictRecord]:
        """Detect conflicts in incoming event"""
        try:
            event_type = event.get("event_type", "")
            data = event.get("data", {})

            # SIGNAL_CONTRADICTION
            if event_type == "SIGNAL_CONTRADICTION":
                agents = data.get("agents_involved", [])
                description = f"Contradictory signals from: {', '.join(agents)}"
                conflict = ConflictRecord(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type=ConflictType.SIGNAL_CONTRADICTION,
                    agents_involved=agents,
                    description=description,
                    escalation=False,
                    created_at=datetime.utcnow().isoformat(),
                )
                return conflict

            # BUDGET_EXCEEDED
            if event_type == "BUDGET_EXCEEDED":
                conflict = ConflictRecord(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type=ConflictType.BUDGET_EXCEEDED,
                    agents_involved=["platform", "marketing"],
                    description="Budget allocation conflict detected",
                    escalation=True,
                    created_at=datetime.utcnow().isoformat(),
                )
                return conflict

            # DEPENDENCY_FAILURE
            if event_type == "DEPENDENCY_FAILURE":
                conflict = ConflictRecord(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type=ConflictType.DEPENDENCY_FAILURE,
                    agents_involved=data.get("agents_involved", []),
                    description=f"Dependency failure: {data.get('reason', 'unknown')}",
                    escalation=False,
                    created_at=datetime.utcnow().isoformat(),
                )
                return conflict

            return None

        except Exception as e:
            logger.error(f"Error detecting conflict: {e}")
            return None

    def resolve_by_rules(self, conflict: ConflictRecord) -> Optional[str]:
        """Resolve conflict based on predefined rules"""
        try:
            # RULE: Higher priority agents win
            if conflict.conflict_type == ConflictType.SIGNAL_CONTRADICTION:
                agents = conflict.agents_involved
                # Simple rule: last agent mentioned wins
                resolution = f"Last signal wins: {agents[-1] if agents else 'none'}"
                return resolution

            # RULE: Budget conflicts require human decision
            if conflict.conflict_type == ConflictType.BUDGET_EXCEEDED:
                return "BLOCK_ALL_BUDGET_REQUESTS"

            # RULE: Dependency failures fail gracefully
            if conflict.conflict_type == ConflictType.DEPENDENCY_FAILURE:
                return "SKIP_DEPENDENT_STEPS"

            return None

        except Exception as e:
            logger.error(f"Error resolving by rules: {e}")
            return None

    async def escalate_ambiguous(self, conflict: ConflictRecord) -> bool:
        """Escalate ambiguous conflicts to owner"""
        try:
            if conflict.conflict_type in [
                ConflictType.SIGNAL_CONTRADICTION,
                ConflictType.BUDGET_EXCEEDED,
            ]:
                # Get resolution suggestion
                resolution = self.resolve_by_rules(conflict)

                # Send critical alert
                await self.resend.send_critical_system_alert(
                    alert_type="Conflicts Require Resolution",
                    details={
                        "conflict_type": conflict.conflict_type.value,
                        "agents_involved": conflict.agents_involved,
                        "description": conflict.description,
                        "resolution_suggestion": resolution,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # Audit log escalation
                audit_store.write_audit(
                    category=AuditCategory.CONFLICT,
                    action="conflict_escalated",
                    target=f"conflict_{conflict.conflict_id}",
                    details={
                        "conflict_type": conflict.conflict_type.value,
                        "resolution": resolution,
                    },
                    outcome="escalated",
                )

                logger.warning(f"Escalated conflict {conflict.conflict_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error escalating ambiguous conflict: {e}")
            return False

    def record_resolution(self, conflict_id: str, resolution: str, detail: Optional[dict] = None):
        """Record conflict resolution"""
        try:
            conflict = conflict_store.get_open_conflicts()[0] if conflict_id else None
            if not conflict:
                logger.error(f"Conflict {conflict_id} not found")
                return

            conflict_store.resolve_conflict(
                conflict_id=conflict_id, resolution=resolution, details=detail
            )

            # Audit log
            audit_store.write_audit(
                category=AuditCategory.CONFLICT,
                action="conflict_resolved",
                target=f"conflict_{conflict_id}",
                details={"resolution": resolution, "detail": detail},
                outcome="resolved",
            )

            logger.info(f"Resolved conflict {conflict_id}: {resolution}")

        except Exception as e:
            logger.error(f"Error recording resolution: {e}")


conflict_resolver = ConflictResolver(resend_client=None)

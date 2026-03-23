from typing import TypedDict, Optional
from datetime import datetime
from models import (
    WorkflowInstance,
    WorkflowStatus,
    WorkflowStep,
    EventEnvelope,
    ConflictRecord,
    SupervisorAuditLog,
    PolicyRule,
    AgentHealthRecord,
    OverrideLog,
    AuditCategory,
)


class SupervisorState(TypedDict):
    workflow_instances: dict[str, WorkflowInstance]
    active_workflows: list[WorkflowInstance]
    pending_workflows: list[WorkflowInstance]
    conflicts: dict[str, ConflictRecord]
    policy_rules: dict[str, PolicyRule]
    agent_health: dict[str, AgentHealthRecord]
    audit_log: list[SupervisorAuditLog]
    override_log: list[OverrideLog]
    status: str  # "running", "degraded", "offline"


def make_initial_state() -> SupervisorState:
    """Initialize supervisor state"""
    return {
        "workflow_instances": {},
        "active_workflows": [],
        "pending_workflows": [],
        "conflicts": {},
        "policy_rules": {},
        "agent_health": {},
        "audit_log": [],
        "override_log": [],
        "status": "running",
    }

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional


class WorkflowType(str, Enum):
    THEME_LAUNCH = "theme_launch"
    THEME_UPDATE = "theme_update"
    SEASONAL_CAMPAIGN = "seasonal_campaign"
    SYSTEM_RECOVERY = "system_recovery"
    BATCH_CONTENT = "batch_content"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConflictType(str, Enum):
    SIGNAL_CONTRADICTION = "signal_contradiction"
    BUDGET_EXCEEDED = "budget_exceeded"
    DEPENDENCY_FAILURE = "dependency_failure"


class AgentHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AuditCategory(str, Enum):
    WORKFLOW = "workflow"
    CONFLICT = "conflict"
    POLICY = "policy"
    OVERRIDE = "override"


class AgentCriticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorkflowStep:
    step_number: int
    agent_name: str
    action: str
    status: WorkflowStatus
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WorkflowInstance:
    instance_id: str
    workflow_type: WorkflowType
    business_key: str
    theme_slug: Optional[str] = None
    correlation_id: Optional[str] = None
    current_step: int = 0
    total_steps: int = 0
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_step: Optional[int] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    context: Optional[dict] = None
    step_history: list[WorkflowStep] = field(default_factory=list)


@dataclass
class EventEnvelope:
    event_id: str
    event_type: str
    data: dict
    correlation_id: str
    causation_id: str
    workflow_id: Optional[str] = None
    timestamp: str = ""


@dataclass
class ConflictRecord:
    conflict_id: str
    conflict_type: ConflictType
    agents_involved: list[str]
    description: str
    created_at: str = ""
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None
    escalated: bool = False


@dataclass
class AgentHealthRecord:
    agent_name: str
    status: AgentHealthStatus
    last_heartbeat: Optional[str] = None
    queue_depth: int = 0
    active_jobs: int = 0
    error_rate: float = 0.0
    mode: str = "normal"
    last_checked: str = ""
    issues: list[str] = field(default_factory=list)


@dataclass
class PolicyRule:
    policy_id: str
    rule_type: str
    condition: dict
    action: str
    value: Optional[float] = None
    active: bool = True
    created_at: str = ""
    expires_at: Optional[str] = None


@dataclass
class SupervisorAuditLog:
    log_id: str
    category: AuditCategory
    action: str
    target: str
    workflow_id: Optional[str] = None
    correlation_id: Optional[str] = None
    details: Optional[dict] = None
    outcome: str = ""
    created_at: str = ""


@dataclass
class OverrideLog:
    override_id: str
    supervisor_decision: str
    overridden_agent: str
    original_signal: dict
    override_reason: str
    applied_at: str = ""
    outcome: str = ""


ALLOWED_WORKFLOW_TRANSITIONS = {
    WorkflowStatus.PENDING: [WorkflowStatus.RUNNING],
    WorkflowStatus.RUNNING: [WorkflowStatus.WAITING, WorkflowStatus.FAILED],
    WorkflowStatus.WAITING: [WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED],
    WorkflowStatus.COMPLETED: [],  # Terminal state
    WorkflowStatus.FAILED: [],  # Terminal state
    WorkflowStatus.CANCELLED: [],  # Terminal state
}

TERMINAL_STATES = {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}

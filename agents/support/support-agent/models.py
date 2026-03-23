from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Platform(str, Enum):
    """Support platform enumeration."""

    HELPSCOUT = "helpscout"
    FACEBOOK = "facebook"


class IntentCategory(str, Enum):
    """Intent category classification."""

    TECHNICAL = "technical"
    BILLING = "billing"
    GENERAL = "general"
    LICENSE = "license"


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskFlag(str, Enum):
    """Risk flags for escalation."""

    BILLING_DISPUTE = "billing_dispute"
    LEGAL_THREAT = "legal_threat"
    CHURN_RISK = "churn_risk"
    ACCOUNT_ISSUE = "account_issue"


@dataclass
class SupportTicket:
    """Represents a support ticket from a platform."""

    ticket_id: str
    platform: Platform
    conversation_id: Optional[str] = None
    customer_email: Optional[str] = None
    order_id: Optional[str] = None
    license_key: Optional[str] = None
    customer_name: Optional[str] = None
    message: str = ""
    subject: Optional[str] = None
    is_html: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority: RiskLevel = RiskLevel.LOW


@dataclass
class Identity:
    """Customer identity information."""

    email: Optional[str] = None
    order_id: Optional[str] = None
    license_key: Optional[str] = None
    customer_name: Optional[str] = None


@dataclass
class IntentClassification:
    """Intent classification results."""

    category: IntentCategory
    confidence: float
    extracted_keywords: List[str]


@dataclass
class RiskFlags:
    """Risk flags for escalation."""

    flags: List[RiskFlag]
    risk_level: RiskLevel
    reason: Optional[str] = None


@dataclass
class RetrievalResult:
    """Result from knowledge base retrieval."""

    collection: str
    text: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class SupportAnswer:
    """Support answer with disclaimer."""

    answer: str
    disclaimer: str
    sources: List[str]
    confidence: float


@dataclass
class AnswerIssues:
    """Issues found in generated answer."""

    issues: List[str]
    confidence_score: float


@dataclass
class EscalationRecord:
    """Escalation record for unresolved tickets."""

    escalation_id: str
    ticket_id: str
    ticket_platform: Platform
    escalation_reason: str
    original_message: str
    customer_identity: Dict[str, Any]
    current_agent_context: str
    escalation_time: datetime
    resolution_status: str = "pending"


@dataclass
class ExecutionLog:
    """Execution log for tracking processing."""

    execution_id: str
    ticket_id: str
    platform: Platform
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, completed, failed
    error_message: Optional[str] = None


@dataclass
class KnowledgeUpdate:
    """Knowledge base update record."""

    update_id: str
    collection: str
    document_id: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

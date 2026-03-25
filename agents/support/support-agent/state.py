from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel



class SupportState(BaseModel):
    """State for support workflows."""

    # Core ticket information
    ticket: Optional[Any] = None
    platform: Optional[str] = None

    # Identity resolution
    identity: Optional[Any] = None

    # Classification results
    intent: Optional[Any] = None
    risk_flags: Optional[Any] = None

    # Retrieval results
    retrieval_results: List[Any] = []

    # Answer generation
    answer: Optional[Any] = None
    answer_issues: Optional[Any] = None

    # Execution tracking
    execution_id: Optional[str] = None
    execution_status: str = "pending"

    # Recurring issue detection
    recurring_issue_detected: bool = False

    # Event logging
    events: List[Dict[str, Any]] = []


def make_initial_state() -> SupportState:
    """Create initial support state."""
    return SupportState()


def update_state_with_ticket(state: SupportState, ticket: Any) -> SupportState:
    """Update state with a support ticket."""
    return SupportState(
        ticket=ticket,
        platform=ticket.platform if hasattr(ticket, "platform") else None,
        execution_id=f"execution_{int(datetime.now(timezone.utc).timestamp())}",
        events=[],
    )


def update_state_with_identity(state: SupportState, identity: Any) -> SupportState:
    """Update state with resolved identity."""
    return SupportState(
        ticket=state.ticket,
        platform=state.platform,
        identity=identity,
        intent=state.intent,
        risk_flags=state.risk_flags,
        retrieval_results=state.retrieval_results,
        answer=state.answer,
        answer_issues=state.answer_issues,
        execution_id=state.execution_id,
        execution_status=state.execution_status,
        recurring_issue_detected=state.recurring_issue_detected,
        events=state.events,
    )


def update_state_with_classification(
    state: SupportState, intent: Any, risk: Any
) -> SupportState:
    """Update state with classification results."""
    return SupportState(
        ticket=state.ticket,
        platform=state.platform,
        identity=state.identity,
        intent=intent,
        risk_flags=risk,
        retrieval_results=state.retrieval_results,
        answer=state.answer,
        answer_issues=state.answer_issues,
        execution_id=state.execution_id,
        execution_status=state.execution_status,
        recurring_issue_detected=state.recurring_issue_detected,
        events=state.events,
    )


def update_state_with_retrieval(
    state: SupportState, results: List[Any]
) -> SupportState:
    """Update state with retrieval results."""
    return SupportState(
        ticket=state.ticket,
        platform=state.platform,
        identity=state.identity,
        intent=state.intent,
        risk_flags=state.risk_flags,
        retrieval_results=results,
        answer=state.answer,
        answer_issues=state.answer_issues,
        execution_id=state.execution_id,
        execution_status=state.execution_status,
        recurring_issue_detected=state.recurring_issue_detected,
        events=state.events,
    )


def update_state_with_answer(
    state: SupportState, answer: Any, issues: Any
) -> SupportState:
    """Update state with generated answer."""
    return SupportState(
        ticket=state.ticket,
        platform=state.platform,
        identity=state.identity,
        intent=state.intent,
        risk_flags=state.risk_flags,
        retrieval_results=state.retrieval_results,
        answer=answer,
        answer_issues=issues,
        execution_id=state.execution_id,
        execution_status=state.execution_status,
        recurring_issue_detected=state.recurring_issue_detected,
        events=state.events,
    )


def update_state_with_execution_status(
    state: SupportState, status: str, error: Optional[str] = None
) -> SupportState:
    """Update state with execution status."""
    new_events = list(state.events)
    new_events.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "error": error,
        }
    )

    return SupportState(
        ticket=state.ticket,
        platform=state.platform,
        identity=state.identity,
        intent=state.intent,
        risk_flags=state.risk_flags,
        retrieval_results=state.retrieval_results,
        answer=state.answer,
        answer_issues=state.answer_issues,
        execution_id=state.execution_id,
        execution_status=status,
        recurring_issue_detected=state.recurring_issue_detected,
        events=new_events,
    )

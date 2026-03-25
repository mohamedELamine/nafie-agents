import logging
from typing import Optional
from datetime import datetime, timezone
from models import WorkflowInstance, WorkflowStatus
from db.audit_store import audit_store
from db.workflow_store import workflow_store

logger = logging.getLogger("supervisor.state_machine")


def transition_workflow(
    instance: WorkflowInstance, new_status: WorkflowStatus, reason: Optional[str] = None
) -> WorkflowInstance:
    """Transition workflow to new status with validation and audit"""
    try:
        # Validate transition
        if new_status not in ALLOWED_WORKFLOW_TRANSITIONS.get(instance.status, []):
            error_msg = f"Invalid transition from {instance.status} to {new_status}"
            logger.error(error_msg)
            raise ValueError(f"SUP_101: {error_msg}")

        if new_status in TERMINAL_STATES:
            if instance.status in TERMINAL_STATES:
                error_msg = f"Cannot transition {instance.status} to terminal state {new_status}"
                logger.error(error_msg)
                raise ValueError(f"SUP_102: {error_msg}")

        # Audit log transition
        audit_store.write_audit(
            category=AuditCategory.WORKFLOW,
            action=f"transition_to_{new_status.value}",
            target=f"workflow_{instance.instance_id}",
            workflow_id=instance.instance_id,
            details={
                "from_status": instance.status.value,
                "to_status": new_status.value,
                "reason": reason,
            },
            outcome="success",
        )

        # Update instance
        old_status = instance.status
        instance.status = new_status
        instance.updated_at = datetime.now(timezone.utc)

        if new_status == WorkflowStatus.RUNNING and not instance.started_at:
            instance.started_at = datetime.now(timezone.utc)
            instance.started_at = instance.started_at.isoformat()

        if new_status in TERMINAL_STATES and not instance.completed_at:
            instance.completed_at = datetime.now(timezone.utc).isoformat()

        # Save to database
        workflow_store.save(instance)

        logger.info(f"Transitioned workflow {instance.instance_id}: {old_status} -> {new_status}")

        return instance

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error transitioning workflow: {e}")
        raise


def validate_transition(current_status: WorkflowStatus, new_status: WorkflowStatus) -> bool:
    """Validate if transition is allowed"""
    return new_status in ALLOWED_WORKFLOW_TRANSITIONS.get(current_status, [])

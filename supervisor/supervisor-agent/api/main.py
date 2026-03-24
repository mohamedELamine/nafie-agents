from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from typing import Optional
import json

from logging_config import configure_logging, get_logger
from models import WorkflowStatus, WorkflowType
from db.workflow_store import workflow_store
from db.audit_store import audit_store
from db.health_store import health_store
from db.policy_store import policy_store
from db.conflict_store import conflict_store
from agent_registry import AGENT_REGISTRY
from workflows.orchestrator import orchestrator

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Supervisor Agent API",
    description="Supervisor agent for workflow orchestration and conflict resolution",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "supervisor-agent",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "supervisor-agent",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/workflows")
async def list_workflows(status: Optional[WorkflowStatus] = None):
    """List all active workflows"""
    try:
        if status:
            workflows = workflow_store.list_by_status(status)
        else:
            workflows = workflow_store.get_active_workflows()

        return {
            "workflows": [_workflow_to_dict(w) for w in workflows],
            "count": len(workflows),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise


@app.get("/workflows/{instance_id}")
async def get_workflow(instance_id: str):
    """Get workflow details by instance ID"""
    try:
        workflow = workflow_store.get(instance_id)

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {
            "workflow": _workflow_to_dict(workflow),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow: {e}")
        raise


@app.post("/workflows")
async def start_workflow(request: dict):
    """Start a new workflow"""
    try:
        workflow_type_str = request.get("workflow_type")
        context = request.get("context", {})

        if not workflow_type_str:
            raise HTTPException(status_code=400, detail="workflow_type is required")

        from workflow_definitions import WorkflowType

        try:
            workflow_type = WorkflowType(workflow_type_str)

            instance = await orchestrator.start_workflow(
                workflow_type=workflow_type,
                trigger_event={"event_type": "WORKFLOW_START"},
                context=context,
            )

            return {
                "instance": _workflow_to_dict(instance),
                "status": "started",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        raise


@app.delete("/workflows/{instance_id}")
async def cancel_workflow(instance_id: str, reason: Optional[str] = None):
    """Cancel a workflow"""
    try:
        await orchestrator.cancel_workflow(instance_id, reason or "Manual cancellation")

        return {
            "status": "cancelled",
            "instance_id": instance_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cancelling workflow: {e}")
        raise


@app.get("/agents/health")
async def get_agents_health():
    """Get health status of all agents"""
    try:
        all_health = health_store.get_all_health()

        return {
            "agents": {
                name: {
                    "status": health.status.value,
                    "queue_depth": health.queue_depth,
                    "active_jobs": health.active_jobs,
                    "error_rate": health.error_rate,
                    "mode": health.mode,
                    "last_heartbeat": health.last_heartbeat,
                    "last_checked": health.last_checked,
                }
                for name, health in all_health.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting agent health: {e}")
        raise


@app.get("/audit")
async def get_audit_log(category: Optional[str] = None, since: Optional[str] = None):
    """Get audit log with filtering"""
    try:
        from datetime import datetime

        # Parse since parameter
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except:
                pass

        # Get audit log
        if category and since_dt:
            audit_log = audit_store.get_audit_log(category=category, since=since_dt)
        elif category:
            audit_log = audit_store.get_audit_log(category=category)
        elif since_dt:
            audit_log = audit_store.get_audit_log(since=since_dt)
        else:
            audit_log = audit_store.get_audit_log()

        return {
            "audit": [_audit_log_to_dict(a) for a in audit_log],
            "count": len(audit_log),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise


@app.get("/policies")
async def get_policies():
    """Get all active policies"""
    try:
        policies = policy_store.get_active_policies()

        return {
            "policies": [_policy_to_dict(p) for p in policies],
            "count": len(policies),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting policies: {e}")
        raise


@app.put("/policies/{policy_id}")
async def update_policy(policy_id: str, policy_data: dict):
    """Update a policy"""
    try:
        policy = (
            policy_store.get_active_policies()[0] if policy_store.get_active_policies() else None
        )

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        # Update policy
        policy.action = policy_data.get("action", policy.action)
        policy.value = policy_data.get("value", policy.value)

        policy_store.save_policy(policy)

        # Audit log
        audit_store.write_audit(
            category="policy",
            action="policy_updated",
            target=f"policy_{policy_id}",
            details={"changes": policy_data},
            outcome="updated",
        )

        return {
            "status": "updated",
            "policy_id": policy_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        raise


@app.get("/conflicts")
async def get_open_conflicts():
    """Get all open conflicts"""
    try:
        conflicts = conflict_store.get_open_conflicts()

        return {
            "conflicts": [_conflict_to_dict(c) for c in conflicts],
            "count": len(conflicts),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        raise


def _workflow_to_dict(workflow) -> dict:
    """Convert workflow to dict"""
    return {
        "instance_id": workflow.instance_id,
        "workflow_type": workflow.workflow_type.value,
        "business_key": workflow.business_key,
        "theme_slug": workflow.theme_slug,
        "correlation_id": workflow.correlation_id,
        "current_step": workflow.current_step,
        "total_steps": workflow.total_steps,
        "status": workflow.status.value,
        "started_at": workflow.started_at,
        "completed_at": workflow.completed_at,
        "failed_step": workflow.failed_step,
        "failure_reason": workflow.failure_reason,
        "retry_count": workflow.retry_count,
        "context": workflow.context,
        "step_history": [_step_to_dict(s) for s in workflow.step_history],
    }


def _step_to_dict(step) -> dict:
    """Convert workflow step to dict"""
    return {
        "step_number": step.step_number,
        "agent_name": step.agent_name,
        "action": step.action,
        "status": step.status.value,
        "started_at": step.started_at,
        "completed_at": step.completed_at,
        "error": step.error,
    }


def _audit_log_to_dict(audit) -> dict:
    """Convert audit log to dict"""
    return {
        "log_id": audit.log_id,
        "category": audit.category.value,
        "action": audit.action,
        "target": audit.target,
        "workflow_id": audit.workflow_id,
        "correlation_id": audit.correlation_id,
        "details": audit.details,
        "outcome": audit.outcome,
        "created_at": audit.created_at,
    }


def _policy_to_dict(policy) -> dict:
    """Convert policy to dict"""
    return {
        "policy_id": policy.policy_id,
        "rule_type": policy.rule_type,
        "condition": policy.condition,
        "action": policy.action,
        "value": policy.value,
        "active": policy.active,
        "created_at": policy.created_at,
        "expires_at": policy.expires_at,
    }


def _conflict_to_dict(conflict) -> dict:
    """Convert conflict to dict"""
    return {
        "conflict_id": conflict.conflict_id,
        "conflict_type": conflict.conflict_type.value,
        "agents_involved": conflict.agents_involved,
        "description": conflict.description,
        "resolution": conflict.resolution,
        "resolved_at": conflict.resolved_at,
        "escalated": conflict.escalated,
        "created_at": conflict.created_at,
    }

import logging
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from models import (
    AuditCategory,
    TERMINAL_STATES,
    WorkflowStatus,
    WorkflowStep,
    WorkflowInstance,
    WorkflowType,
    EventEnvelope,
)
from agent_registry import get_agent
from db.workflow_store import workflow_store
from db.audit_store import audit_store
from db.conflict_store import conflict_store
from db.health_store import health_store
from db.policy_store import policy_store
from redis_bus import redis_bus
from policy_engine import check_user_locked, evaluate_policies

logger = logging.getLogger("supervisor.orchestrator")


class WorkflowOrchestrator:
    def __init__(
        self, workflow_store, audit_store, conflict_store, health_store, policy_store, resend_client
    ):
        self.workflow_store = workflow_store
        self.audit_store = audit_store
        self.conflict_store = conflict_store
        self.health_store = health_store
        self.policy_store = policy_store
        self.resend = resend_client

    async def start_workflow(
        self,
        workflow_type: WorkflowType,
        trigger_event: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowInstance]:
        """Start a new workflow with idempotency check"""
        try:
            from workflow_definitions import WORKFLOW_DEFINITIONS, build_workflow_business_key
            context_data = context or {}

            # Build business key
            business_key = build_workflow_business_key(workflow_type, context_data)

            # Check idempotency
            existing = self.workflow_store.get_by_business_key(business_key)
            if existing:
                logger.warning(
                    f"Workflow with business_key {business_key} already exists: {existing.instance_id}"
                )
                return existing

            # Validate all agents are registered
            steps = WORKFLOW_DEFINITIONS[workflow_type].get("steps", [])
            for step in steps:
                agent = get_agent(step["agent"])
                if not agent:
                    error_msg = f"Agent {step['agent']} not registered"
                    logger.error(error_msg)
                    self.audit_store.write_audit(
                        category=AuditCategory.WORKFLOW,
                        action="workflow_start_failed",
                        target=f"workflow_{workflow_type.value}",
                        details={"reason": error_msg},
                        outcome="error",
                    )
                    raise ValueError(f"SUP_001: {error_msg}")

            # Check user locked decisions
            if context_data and check_user_locked(context_data.get("decision_domain", "")):
                error_msg = "User locked decision attempted"
                logger.error(error_msg)
                self.audit_store.write_audit(
                    category=AuditCategory.OVERRIDE,
                    action="user_locked_decision",
                    target=f"workflow_{workflow_type.value}",
                    details={"context": context_data, "reason": "user_locked_decision"},
                    outcome="blocked",
                )
                raise ValueError(f"SUP_301: {error_msg}")

            # Evaluate policies
            policies = evaluate_policies(context_data)
            if policies:
                logger.warning(f"Policy violations during workflow start: {len(policies)}")
                self.audit_store.write_audit(
                    category=AuditCategory.POLICY,
                    action="policy_enforcement",
                    target=f"workflow_{workflow_type.value}",
                    details={"policies": [p.policy_id for p in policies], "count": len(policies)},
                    outcome="warning",
                )

            # Create workflow instance
            instance_id = str(uuid.uuid4())
            total_steps = len(steps)

            instance = WorkflowInstance(
                instance_id=instance_id,
                workflow_type=workflow_type,
                business_key=business_key,
                theme_slug=context_data.get("theme_slug")
                if workflow_type in [WorkflowType.THEME_LAUNCH, WorkflowType.THEME_UPDATE]
                else None,
                correlation_id=context_data.get("correlation_id"),
                current_step=1,
                total_steps=total_steps,
                status=WorkflowStatus.RUNNING,
                retry_count=0,
                context=context_data,
                step_history=[],
            )

            # Save workflow
            instance = self.workflow_store.save(instance)

            # Audit log
            self.audit_store.write_audit(
                category=AuditCategory.WORKFLOW,
                action="workflow_started",
                target=f"workflow_{instance_id}",
                workflow_id=instance_id,
                details={
                    "workflow_type": workflow_type.value,
                    "business_key": business_key,
                    "context": context_data,
                },
                outcome="success",
            )

            logger.info(f"Started workflow {instance_id}: {workflow_type.value}")

            # Publish event
            await redis_bus.publish_supervisor_event(
                channel="supervisor_events",
                event_type="WORKFLOW_STARTED",
                data={
                    "workflow_id": instance_id,
                    "workflow_type": workflow_type.value,
                    "business_key": business_key,
                },
                correlation_id=str(uuid.uuid4()),
                workflow_id=instance_id,
            )

            # Execute first step
            first_step = steps[0]
            await self._execute_step(instance, first_step)

            return instance

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error starting workflow: {e}")
            raise

    async def on_step_completed(
        self, instance_id: str, completed_event: dict, event_data: dict, causation_id: str
    ) -> Optional[WorkflowInstance]:
        """Handle step completion event"""
        try:
            instance = self.workflow_store.get(instance_id)
            if not instance:
                logger.error(f"Workflow {instance_id} not found")
                return None

            if instance.status in TERMINAL_STATES:
                logger.warning(f"Cannot complete step for terminal workflow {instance_id}")
                return None

            # Update current step
            instance.current_step += 1

            # Save step history
            step_history_entry = WorkflowStep(
                step_number=instance.current_step - 1,
                agent_name=completed_event.get("agent_name"),
                action=completed_event.get("action", "unknown"),
                status=WorkflowStatus.COMPLETED,
                started_at=completed_event.get(
                    "started_at",
                    datetime.now(timezone.utc).isoformat(),
                ),
                completed_at=datetime.now(timezone.utc).isoformat(),
                error=completed_event.get("error"),
            )
            self.workflow_store.update_step(instance_id, step_history_entry)
            instance.step_history.append(step_history_entry)

            # Check if workflow is complete
            if instance.current_step >= instance.total_steps:
                await self._emit_workflow_completed(instance)
                return instance
            else:
                # Execute next step
                next_step_data = self._get_next_step(instance)
                if next_step_data:
                    await self._execute_step(instance, next_step_data)
                    return instance
                else:
                    logger.warning(f"No next step for workflow {instance_id}")
                    return instance

        except Exception as e:
            logger.error(f"Error handling step completion: {e}")
            raise

    async def handle_step_timeout(self, instance_id: str, step_number: int):
        """Handle step timeout"""
        try:
            instance = self.workflow_store.get(instance_id)
            if not instance:
                return

            instance.status = WorkflowStatus.FAILED
            instance.failed_step = step_number
            instance.failure_reason = f"Step {step_number} timeout"

            self.workflow_store.save(instance)

            # Update step history
            step_history_entry = WorkflowStep(
                step_number=step_number,
                agent_name="unknown",
                action="timeout",
                status=WorkflowStatus.FAILED,
                started_at=datetime.now(timezone.utc).isoformat(),
                error="Step timeout",
            )
            self.workflow_store.update_step(instance_id, step_history_entry)
            instance.step_history.append(step_history_entry)

            # Emit workflow failed
            await self._emit_workflow_failed(instance)

        except Exception as e:
            logger.error(f"Error handling step timeout: {e}")

    async def cancel_workflow(self, instance_id: str, reason: str):
        """Cancel a workflow"""
        try:
            instance = self.workflow_store.get(instance_id)
            if not instance:
                logger.error(f"Workflow {instance_id} not found")
                return

            if instance.status in TERMINAL_STATES:
                logger.warning(f"Cannot cancel terminal workflow {instance_id}")
                return

            instance.status = WorkflowStatus.CANCELLED
            instance.completed_at = datetime.now(timezone.utc).isoformat()

            self.workflow_store.save(instance)

            # Audit log
            self.audit_store.write_audit(
                category=AuditCategory.WORKFLOW,
                action="workflow_cancelled",
                target=f"workflow_{instance_id}",
                workflow_id=instance_id,
                details={"reason": reason},
                outcome="cancelled",
            )

            logger.info(f"Cancelled workflow {instance_id}: {reason}")

        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}")

    async def _execute_step(self, instance: WorkflowInstance, step: dict):
        """Execute a workflow step by publishing event"""
        try:
            from workflow_definitions import WORKFLOW_DEFINITIONS

            workflow_config = WORKFLOW_DEFINITIONS[instance.workflow_type]
            total_steps = len(workflow_config["steps"])

            # Update current step
            instance.current_step = step["step_number"]
            instance.total_steps = total_steps
            self.workflow_store.save(instance)

            # Create event envelope
            event = EventEnvelope(
                event_id=str(uuid.uuid4()),
                event_type=f"{step['action']}_trigger",
                data={
                    "workflow_id": instance.instance_id,
                    "workflow_type": instance.workflow_type.value,
                    "step_number": step["step_number"],
                    "agent_name": step["agent"],
                    "action": step["action"],
                    "parallel": step.get("parallel", False),
                },
                correlation_id=instance.correlation_id,
                causation_id=instance.instance_id,
                workflow_id=instance.instance_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # Get agent channel
            channel = f"agent:{step['agent']}:events"

            # Publish event
            await redis_bus.publish_supervisor_event(
                channel=channel,
                event_type=event.event_type,
                data=event.data,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                workflow_id=event.workflow_id,
            )

            # Update step history
            step_history_entry = WorkflowStep(
                step_number=step["step_number"],
                agent_name=step["agent"],
                action=step["action"],
                status=WorkflowStatus.RUNNING,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self.workflow_store.update_step(instance.instance_id, step_history_entry)
            instance.step_history.append(step_history_entry)

            logger.info(f"Executed step {step['step_number']} for workflow {instance.instance_id}")

        except Exception as e:
            logger.error(f"Error executing step: {e}")
            raise

    async def _emit_workflow_completed(self, instance: WorkflowInstance):
        """Emit workflow completed event"""
        try:
            instance.status = WorkflowStatus.COMPLETED
            self.workflow_store.save(instance)

            # Audit log
            self.audit_store.write_audit(
                category=AuditCategory.WORKFLOW,
                action="workflow_completed",
                target=f"workflow_{instance.instance_id}",
                workflow_id=instance.instance_id,
                details={
                    "steps_completed": instance.current_step,
                    "total_steps": instance.total_steps,
                },
                outcome="success",
            )

            logger.info(f"Workflow {instance.instance_id} completed")

            # Publish event
            await redis_bus.publish_supervisor_event(
                channel="supervisor_events",
                event_type="WORKFLOW_COMPLETED",
                data={
                    "workflow_id": instance.instance_id,
                    "workflow_type": instance.workflow_type.value,
                    "business_key": instance.business_key,
                    "status": "completed",
                },
                correlation_id=instance.correlation_id,
                workflow_id=instance.instance_id,
            )

        except Exception as e:
            logger.error(f"Error emitting workflow completed: {e}")

    async def _emit_workflow_failed(self, instance: WorkflowInstance):
        """Emit workflow failed event"""
        try:
            instance.status = WorkflowStatus.FAILED
            self.workflow_store.save(instance)

            # Audit log
            self.audit_store.write_audit(
                category=AuditCategory.WORKFLOW,
                action="workflow_failed",
                target=f"workflow_{instance.instance_id}",
                workflow_id=instance.instance_id,
                details={"failed_step": instance.failed_step, "reason": instance.failure_reason},
                outcome="failed",
            )

            logger.error(f"Workflow {instance.instance_id} failed: {instance.failure_reason}")

            # Publish event
            await redis_bus.publish_supervisor_event(
                channel="supervisor_events",
                event_type="WORKFLOW_FAILED",
                data={
                    "workflow_id": instance.instance_id,
                    "workflow_type": instance.workflow_type.value,
                    "business_key": instance.business_key,
                    "reason": instance.failure_reason,
                },
                correlation_id=instance.correlation_id,
                workflow_id=instance.instance_id,
            )

            # Send critical alert if workflow is CRITICAL
            if instance.workflow_type in [WorkflowType.THEME_LAUNCH, WorkflowType.SYSTEM_RECOVERY]:
                await self.resend.send_critical_system_alert(
                    alert_type="Workflow Failure",
                    details={
                        "workflow_id": instance.instance_id,
                        "workflow_type": instance.workflow_type.value,
                        "failure_reason": instance.failure_reason,
                        "failed_step": instance.failed_step,
                    },
                )

        except Exception as e:
            logger.error(f"Error emitting workflow failed: {e}")

    async def _handle_parallel_group(
        self, instance: WorkflowInstance, steps: list, group_name: str
    ):
        """Handle parallel steps"""
        try:
            from asyncio import gather

            logger.info(f"Handling parallel group {group_name} for workflow {instance.instance_id}")

            tasks = []
            for step in steps:
                tasks.append(self._execute_step(instance, step))

            results = await gather(*tasks, return_exceptions=True)

            failed = [r for r in results if isinstance(r, Exception)]
            if failed:
                logger.warning(f"Parallel group {group_name} completed with {len(failed)} failures")

        except Exception as e:
            logger.error(f"Error handling parallel group: {e}")

    def _get_next_step(self, instance: WorkflowInstance) -> Optional[dict]:
        """Get next step for workflow"""
        try:
            from workflow_definitions import WORKFLOW_DEFINITIONS

            workflow_config = WORKFLOW_DEFINITIONS[instance.workflow_type]
            steps = workflow_config.get("steps", [])

            if instance.current_step < len(steps):
                return steps[instance.current_step - 1]  # Current step is already done

            return None

        except Exception as e:
            logger.error(f"Error getting next step: {e}")
            return None


orchestrator = WorkflowOrchestrator(
    workflow_store=workflow_store,
    audit_store=audit_store,
    conflict_store=conflict_store,
    health_store=health_store,
    policy_store=policy_store,
    resend_client=None,
)

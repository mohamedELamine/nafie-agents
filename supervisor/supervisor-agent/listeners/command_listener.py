import logging
import asyncio
from typing import Optional, Dict, Any
import json
from redis_bus import redis_bus
from workflows.orchestrator import orchestrator
from agent_registry import AGENT_REGISTRY

logger = logging.getLogger("supervisor.command_listener")


class CommandListener:
    def __init__(self):
        self.running = False

    async def start(self):
        """Start listening for command events"""
        try:
            self.running = True
            logger.info("Starting command listener")

            # Ensure consumer groups exist
            await redis_bus.ensure_consumer_group(channel="workflow_commands", group="supervisor")

            # Start consuming commands
            while self.running:
                try:
                    await self._consume_commands()
                except Exception as e:
                    logger.error(f"Error in command listener loop: {e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error starting command listener: {e}")
            self.running = False

    async def stop(self):
        """Stop command listener"""
        try:
            self.running = False
            logger.info("Stopping command listener")
        except Exception as e:
            logger.error(f"Error stopping command listener: {e}")

    async def _consume_commands(self):
        """Consume commands from Redis"""
        try:
            from workflow_definitions import WorkflowType

            message = await redis_bus.read_group(
                channel="workflow_commands", group="supervisor", consumer="command_listener"
            )

            if not message:
                await asyncio.sleep(1)
                return

            # Process message
            await self._process_command(message)

            # Acknowledge message
            await redis_bus.ack(
                channel="workflow_commands", group="supervisor", message_id=message["id"]
            )

        except Exception as e:
            logger.error(f"Error consuming commands: {e}")

    async def _process_command(self, message: dict):
        """Process incoming command"""
        try:
            from models import EventEnvelope

            event_type = message["data"].get("event_type", "")
            event_data = message["data"].get("data", {})

            logger.info(f"Processing command: {event_type}")

            # Handle workflow start
            if event_type == "WORKFLOW_START":
                await self._handle_workflow_start(event_data)

            # Handle agent pause/resume
            elif event_type == "AGENT_PAUSE":
                await self._handle_agent_pause(event_data)

            elif event_type == "AGENT_RESUME":
                await self._handle_agent_resume(event_data)

            # Handle policy updates
            elif event_type == "POLICY_UPDATE":
                await self._handle_policy_update(event_data)

            # Handle workflow cancellation
            elif event_type == "WORKFLOW_CANCEL":
                await self._handle_workflow_cancel(event_data)

            # Handle critical system alert
            elif event_type == "CRITICAL_SYSTEM_ALERT":
                await self._handle_critical_alert(event_data)

            else:
                logger.warning(f"Unknown command type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing command: {e}")

    async def _handle_workflow_start(self, data: dict):
        """Handle workflow start command"""
        try:
            workflow_type = data.get("workflow_type")
            context = data.get("context", {})

            if workflow_type:
                from workflow_definitions import WorkflowType

                try:
                    workflow_enum = WorkflowType(workflow_type)
                    instance = await orchestrator.start_workflow(
                        workflow_type=workflow_enum, trigger_event=data, context=context
                    )

                    logger.info(f"Started workflow {instance.instance_id}")

                except ValueError as e:
                    logger.error(f"Invalid workflow type: {workflow_type} - {e}")

        except Exception as e:
            logger.error(f"Error handling workflow start: {e}")

    async def _handle_agent_pause(self, data: dict):
        """Handle agent pause command"""
        try:
            from redis_bus import redis_bus

            agent_name = data.get("agent_name")

            if agent_name and agent_name in AGENT_REGISTRY:
                # Check if decision domain is user locked
                if (
                    data.get("decision_domain")
                    and data.get("domain") in AGENT_REGISTRY[agent_name].degraded_fallback
                ):
                    logger.error(f"Cannot pause CRITICAL agent {agent_name}: USER_LOCKED_DECISIONS")
                    return

                # Publish pause event to agent
                await redis_bus.publish_supervisor_event(
                    channel=f"agent:{agent_name}:events",
                    event_type="AGENT_PAUSE",
                    data={"reason": data.get("reason", "Manual pause from supervisor")},
                )

                logger.info(f"Published pause command for agent {agent_name}")

            else:
                logger.error(f"Agent {agent_name} not found in registry")

        except Exception as e:
            logger.error(f"Error handling agent pause: {e}")

    async def _handle_agent_resume(self, data: dict):
        """Handle agent resume command"""
        try:
            from redis_bus import redis_bus

            agent_name = data.get("agent_name")

            if agent_name and agent_name in AGENT_REGISTRY:
                # Publish resume event to agent
                await redis_bus.publish_supervisor_event(
                    channel=f"agent:{agent_name}:events",
                    event_type="AGENT_RESUME",
                    data={"reason": data.get("reason", "Manual resume from supervisor")},
                )

                logger.info(f"Published resume command for agent {agent_name}")

            else:
                logger.error(f"Agent {agent_name} not found in registry")

        except Exception as e:
            logger.error(f"Error handling agent resume: {e}")

    async def _handle_policy_update(self, data: dict):
        """Handle policy update command"""
        try:
            from db.policy_store import policy_store
            from datetime import datetime
            import uuid

            policy_id = data.get("policy_id")
            policy_data = data.get("policy_data", {})

            if policy_id and policy_data:
                # Update policy
                policy = policy_store.get_active_policies()[0]  # Simplified

                # Update policy values
                policy.action = policy_data.get("action", policy.action)
                policy.value = policy_data.get("value", policy.value)

                policy_store.save_policy(policy)

                logger.info(f"Updated policy {policy_id}")

        except Exception as e:
            logger.error(f"Error handling policy update: {e}")

    async def _handle_workflow_cancel(self, data: dict):
        """Handle workflow cancel command"""
        try:
            workflow_id = data.get("workflow_id")
            reason = data.get("reason", "Manual cancellation from owner")

            if workflow_id:
                await orchestrator.cancel_workflow(workflow_id, reason)
                logger.info(f"Cancelled workflow {workflow_id}")

        except Exception as e:
            logger.error(f"Error handling workflow cancel: {e}")

    async def _handle_critical_alert(self, data: dict):
        """Handle critical system alert command"""
        try:
            alert_type = data.get("alert_type")
            details = data.get("details", {})

            if alert_type and "resend" in globals():
                await resend.send_critical_system_alert(alert_type=alert_type, details=details)

            logger.warning(f"Processed critical alert: {alert_type}")

        except Exception as e:
            logger.error(f"Error handling critical alert: {e}")


command_listener = CommandListener()

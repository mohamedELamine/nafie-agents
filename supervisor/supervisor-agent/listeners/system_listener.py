import logging
import asyncio
from models import AgentHealthStatus
from redis_bus import redis_bus
from workflows.health_monitor import health_monitor
from workflows.orchestrator import orchestrator
from workflows.conflict_resolver import conflict_resolver

logger = logging.getLogger("supervisor.system_listener")


class SystemListener:
    def __init__(self, resend_client=None):
        self.running = False
        self.resend = resend_client

    async def start(self):
        """Start listening for system events"""
        try:
            self.running = True
            logger.info("Starting system listener")

            # Ensure consumer groups exist
            await redis_bus.ensure_consumer_group(channel="supervisor_events", group="supervisor")

            # Start consuming events
            while self.running:
                try:
                    await self._consume_events()
                except Exception as e:
                    logger.error(f"Error in system listener loop: {e}")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error starting system listener: {e}")
            self.running = False

    async def stop(self):
        """Stop system listener"""
        try:
            self.running = False
            logger.info("Stopping system listener")
        except Exception as e:
            logger.error(f"Error stopping system listener: {e}")

    async def _consume_events(self):
        """Consume events from Redis"""
        try:
            message = await redis_bus.read_group(
                channel="supervisor_events", group="supervisor", consumer="listener"
            )

            if not message:
                await asyncio.sleep(1)
                return

            # Process message
            await self._process_message(message)

            # Acknowledge message
            await redis_bus.ack(
                channel="supervisor_events", group="supervisor", message_id=message["id"]
            )

        except Exception as e:
            logger.error(f"Error consuming events: {e}")
            raise

    async def _process_message(self, message: dict):
        """Process incoming message"""
        try:
            event_type = message["data"].get("event_type", "")
            event_data = message["data"].get("data", {})

            logger.info(f"Processing event: {event_type}")

            # Handle heartbeats
            if event_type == "HEARTBEAT":
                await self._handle_heartbeat(event_data)

            # Handle workflow events
            elif event_type == "STEP_COMPLETED":
                await self._handle_step_completed(event_data)

            # Handle conflicts
            elif event_type == "CONFLICT_DETECTED":
                await self._handle_conflict(event_data)

            # Handle agent events
            elif event_type == "AGENT_STATUS_CHANGED":
                await self._handle_agent_status(event_data)

            # Handle system alerts
            elif event_type == "SYSTEM_ALERT":
                await self._handle_system_alert(event_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_heartbeat(self, data: dict):
        """Process agent heartbeat"""
        try:
            agent_name = data.get("agent_name")
            heartbeat_data = data.get("heartbeat", {})

            if agent_name:
                await health_monitor.process_heartbeat(agent_name, heartbeat_data)

        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")

    async def _handle_step_completed(self, data: dict):
        """Handle workflow step completion"""
        try:
            workflow_id = data.get("workflow_id")
            event_data = data.get("event_data", {})

            if workflow_id:
                await orchestrator.on_step_completed(
                    instance_id=workflow_id,
                    completed_event=data,
                    event_data=event_data,
                    causation_id=data.get("causation_id"),
                )

        except Exception as e:
            logger.error(f"Error handling step completion: {e}")

    async def _handle_conflict(self, data: dict):
        """Handle conflict detection"""
        try:
            conflict = conflict_resolver.detect_conflict(data)

            if conflict:
                await self._handle_conflict_resolution(conflict)

        except Exception as e:
            logger.error(f"Error handling conflict: {e}")

    async def _handle_conflict_resolution(self, conflict: dict):
        """Handle conflict resolution"""
        try:
            from db.audit_store import audit_store

            # Try to resolve by rules
            resolution = conflict_resolver.resolve_by_rules(conflict)

            if resolution:
                # Log resolution
                conflict_resolver.record_resolution(
                    conflict_id=conflict.conflict_id, resolution=resolution
                )

                # Escalate if needed
                if conflict.escalated or not resolution:
                    await conflict_resolver.escalate_ambiguous(conflict)

        except Exception as e:
            logger.error(f"Error handling conflict resolution: {e}")

    async def _handle_agent_status(self, data: dict):
        """Handle agent status changes"""
        try:
            agent_name = data.get("agent_name")
            new_status = data.get("status")

            if agent_name and new_status:
                health = await health_monitor._check_agent_health(agent_name)
                try:
                    health.status = AgentHealthStatus(new_status)
                except ValueError:
                    logger.warning(f"Unknown agent status for {agent_name}: {new_status}")
                    return

                # Apply degraded mode
                health_monitor.apply_degraded_mode(agent_name, health.status)

        except Exception as e:
            logger.error(f"Error handling agent status: {e}")

    async def _handle_system_alert(self, data: dict):
        """Handle system alerts"""
        try:
            alert_type = data.get("alert_type")
            details = data.get("details", {})

            if alert_type and self.resend:
                await self.resend.send_critical_system_alert(
                    alert_type=alert_type,
                    details=details,
                )

        except Exception as e:
            logger.error(f"Error handling system alert: {e}")


system_listener = SystemListener()

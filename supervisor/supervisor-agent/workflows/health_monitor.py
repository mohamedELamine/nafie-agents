import logging
from typing import Dict, Any, Optional
from datetime import datetime
from models import AgentHealthStatus, AgentHealthRecord
from db.health_store import health_store
from redis_bus import redis_bus

logger = logging.getLogger("supervisor.health_monitor")


class HealthMonitor:
    def __init__(self, resend_client):
        self.resend = resend_client
        self.last_health_check = None

    async def check_all_agents(self) -> Dict[str, AgentHealthRecord]:
        """Check health of all agents"""
        try:
            from agent_registry import AGENT_REGISTRY, get_degraded_action

            all_health = {}

            for agent_name in AGENT_REGISTRY.keys():
                health_record = await self._check_agent_health(agent_name)
                all_health[agent_name] = health_record

            self.last_health_check = datetime.utcnow()

            # Check for unhealthy agents
            await self._handle_unhealthy_agents(all_health)

            # Emit health check event
            await self._emit_health_check_event(all_health)

            return all_health

        except Exception as e:
            logger.error(f"Error checking all agents: {e}")
            raise

    async def _check_agent_health(self, agent_name: str) -> AgentHealthRecord:
        """Check health of specific agent"""
        try:
            # Default healthy status
            health = AgentHealthRecord(
                agent_name=agent_name,
                status=AgentHealthStatus.HEALTHY,
                last_heartbeat=datetime.utcnow().isoformat(),
                queue_depth=0,
                active_jobs=0,
                error_rate=0.0,
                mode="normal",
                last_checked=datetime.utcnow().isoformat(),
                issues=[],
            )

            # Check if agent exists in registry
            agent = get_agent(agent_name)
            if not agent:
                health.status = AgentHealthStatus.UNKNOWN
                health.issues = ["Agent not registered"]
            else:
                # Check degraded mode
                degraded_action = get_degraded_action(agent_name)
                if degraded_action:
                    health.mode = "degraded"
                    health.status = AgentHealthStatus.DEGRADED
                    health.issues = [f"Degraded mode: {degraded_action}"]

            health_store.save_health_record(agent_name, health)

            logger.info(f"Health check for {agent_name}: {health.status.value}")

            return health

        except Exception as e:
            logger.error(f"Error checking health for {agent_name}: {e}")
            raise

    async def _handle_unhealthy_agents(self, all_health: Dict[str, AgentHealthRecord]):
        """Handle unhealthy agents"""
        try:
            unhealthy_agents = [
                name
                for name, health in all_health.items()
                if health.status
                in [
                    AgentHealthStatus.DEGRADED,
                    AgentHealthStatus.UNHEALTHY,
                    AgentHealthStatus.UNKNOWN,
                ]
            ]

            if unhealthy_agents:
                logger.warning(f"Unhealthy agents detected: {', '.join(unhealthy_agents)}")

                # Apply degraded mode rules
                for agent_name in unhealthy_agents:
                    agent = get_agent(agent_name)
                    if agent and agent.degraded_fallback:
                        mode = agent.degraded_fallback.get("mode", "manual_review")
                        logger.info(f"Applying degraded mode for {agent_name}: {mode}")

        except Exception as e:
            logger.error(f"Error handling unhealthy agents: {e}")

    async def _emit_health_check_event(self, all_health: Dict[str, AgentHealthRecord]):
        """Emit health check event"""
        try:
            await redis_bus.publish_supervisor_event(
                channel="supervisor_events",
                event_type="HEALTH_CHECK",
                data={
                    "timestamp": datetime.utcnow().isoformat(),
                    "agents": {name: health.status.value for name, health in all_health.items()},
                },
            )

        except Exception as e:
            logger.error(f"Error emitting health check event: {e}")

    async def process_heartbeat(
        self, agent_name: str, heartbeat_data: Dict[str, Any]
    ) -> AgentHealthRecord:
        """Process agent heartbeat"""
        try:
            health = AgentHealthRecord(
                agent_name=agent_name,
                status=AgentHealthStatus.HEALTHY,
                last_heartbeat=datetime.utcnow().isoformat(),
                queue_depth=heartbeat_data.get("queue_depth", 0),
                active_jobs=heartbeat_data.get("active_jobs", 0),
                error_rate=heartbeat_data.get("error_rate", 0.0),
                mode="normal",
                last_checked=datetime.utcnow().isoformat(),
                issues=[],
            )

            health_store.save_health_record(agent_name, health)

            logger.info(f"Heartbeat received from {agent_name}")

            return health

        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
            raise

    def apply_degraded_mode(self, agent_name: str, health_status: AgentHealthStatus):
        """Apply degraded mode for agent"""
        try:
            from agent_registry import get_degraded_action

            degraded_action = get_degraded_action(agent_name)

            if degraded_action:
                logger.info(f"Applying degraded mode for {agent_name}: {degraded_action}")

        except Exception as e:
            logger.error(f"Error applying degraded mode: {e}")

    def _check_heartbeat_timeout(self, agent_name: str) -> bool:
        """Check if agent heartbeat has timed out"""
        try:
            health = health_store.get_health(agent_name)

            if not health or not health.last_heartbeat:
                return True

            from datetime import datetime, timedelta

            last_heartbeat = datetime.fromisoformat(health.last_heartbeat)
            timeout_seconds = 120  # Default from HEARTBEAT_TIMEOUT_SEC

            if datetime.utcnow() - last_heartbeat > timedelta(seconds=timeout_seconds):
                logger.error(f"HEARTBEAT_TIMEOUT: {agent_name}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking heartbeat timeout: {e}")
            return False

    async def get_system_health_summary(self) -> Dict[str, Any]:
        """Get system health summary for dashboard"""
        try:
            all_health = health_store.get_all_health()
            unhealthy = [
                name
                for name, health in all_health.items()
                if health.status in [AgentHealthStatus.DEGRADED, AgentHealthStatus.UNHEALTHY]
            ]

            total_agents = len(all_health)
            unhealthy_count = len(unhealthy)
            healthy_count = total_agents - unhealthy_count

            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_agents": total_agents,
                "healthy_agents": healthy_count,
                "unhealthy_agents": unhealthy_count,
                "unhealthy_list": unhealthy,
                "status": "healthy" if unhealthy_count == 0 else "degraded",
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting system health summary: {e}")
            raise


health_monitor = HealthMonitor(resend_client=None)

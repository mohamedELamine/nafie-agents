from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AgentRegistryEntry:
    agent_name: str
    criticality: str
    description: str
    degraded_fallback: dict = field(default_factory=dict)
    allowed_workflows: list[str] = field(default_factory=list)


AGENT_REGISTRY: dict[str, AgentRegistryEntry] = {
    "builder": AgentRegistryEntry(
        agent_name="builder",
        criticality="HIGH",
        description="Theme builder agent",
        degraded_fallback={
            "mode": "manual_review",
            "fallback_action": "wait_for_review",
            "affected_workflows": ["THEME_LAUNCH", "THEME_UPDATE"],
        },
        allowed_workflows=["THEME_LAUNCH", "THEME_UPDATE", "SYSTEM_RECOVERY"],
    ),
    "visual_production": AgentRegistryEntry(
        agent_name="visual_production",
        criticality="HIGH",
        description="Visual assets generator",
        degraded_fallback={
            "mode": "manual_trigger",
            "fallback_action": "send_manual_trigger",
            "affected_workflows": ["THEME_LAUNCH"],
        },
        allowed_workflows=["THEME_LAUNCH", "THEME_UPDATE"],
    ),
    "platform": AgentRegistryEntry(
        agent_name="platform",
        criticality="CRITICAL",
        description="Platform deployment agent",
        degraded_fallback={
            "mode": "safe_mode",
            "fallback_action": "deploy_with_alerts",
            "affected_workflows": ["THEME_LAUNCH", "THEME_UPDATE"],
        },
        allowed_workflows=["THEME_LAUNCH", "THEME_UPDATE"],
    ),
    "support": AgentRegistryEntry(
        agent_name="support",
        criticality="HIGH",
        description="Support agent",
        degraded_fallback={
            "mode": "escalate_to_human",
            "fallback_action": "forward_to_admin",
            "affected_workflows": ["BATCH_CONTENT", "SYSTEM_RECOVERY"],
        },
        allowed_workflows=["BATCH_CONTENT", "SYSTEM_RECOVERY"],
    ),
    "content": AgentRegistryEntry(
        agent_name="content",
        criticality="MEDIUM",
        description="Content agent",
        degraded_fallback={
            "mode": "continue_without",
            "fallback_action": "skip_content_steps",
            "affected_workflows": ["SEASONAL_CAMPAIGN"],
        },
        allowed_workflows=["SEASONAL_CAMPAIGN", "BATCH_CONTENT"],
    ),
    "marketing": AgentRegistryEntry(
        agent_name="marketing",
        criticality="MEDIUM",
        description="Marketing campaign agent",
        degraded_fallback={
            "mode": "pause_campaigns",
            "fallback_action": "send_pause_alert",
            "affected_workflows": ["SEASONAL_CAMPAIGN"],
        },
        allowed_workflows=["SEASONAL_CAMPAIGN"],
    ),
    "analytics": AgentRegistryEntry(
        agent_name="analytics",
        criticality="MEDIUM",
        description="Analytics agent",
        degraded_fallback={
            "mode": "offline_mode",
            "fallback_action": "collect_and_batch",
            "affected_workflows": ["SEASONAL_CAMPAIGN", "THEME_LAUNCH"],
        },
        allowed_workflows=["SEASONAL_CAMPAIGN", "THEME_LAUNCH", "THEME_UPDATE"],
    ),
    "visual_audio": AgentRegistryEntry(
        agent_name="visual_audio",
        criticality="LOW",
        description="Visual and audio assets agent",
        degraded_fallback={
            "mode": "queue_for_manual",
            "fallback_action": "add_to_manual_queue",
            "affected_workflows": [],
        },
        allowed_workflows=[],
    ),
}

DEGRADED_MODE_RULES: Dict[str, Dict[str, Any]] = {
    "visual_production": {
        "threshold": "CRITICAL",
        "fallback": "send_manual_trigger",
        "notification": "alert_owner",
    },
    "platform": {
        "threshold": "CRITICAL",
        "fallback": "safe_mode",
        "notification": "alert_owner_immediate",
    },
}


def get_agent(agent_name: str) -> Optional[AgentRegistryEntry]:
    """Get agent registry entry by name"""
    return AGENT_REGISTRY.get(agent_name)


def get_agents_by_criticality(criticality: str) -> list[AgentRegistryEntry]:
    """Get all agents of a specific criticality"""
    return [entry for entry in AGENT_REGISTRY.values() if entry.criticality == criticality]


def get_degraded_action(agent_name: str) -> Optional[str]:
    """Get degraded action for an agent"""
    agent = get_agent(agent_name)
    if agent and agent.degraded_fallback:
        return agent.degraded_fallback.get("fallback_action")
    return None


REDIS_CHANNELS: Dict[str, str] = {
    "supervisor_events": "supervisor_events",
    "heartbeat_events": "heartbeat_events",
    "workflow_commands": "workflow_commands",
    "agent_health": "agent_health",
}


def get_agent_channel(agent_name: str) -> str:
    """Get Redis channel for agent events"""
    return f"agent:{agent_name}:events"

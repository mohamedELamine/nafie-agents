from enum import Enum


class WorkflowType(str, Enum):
    THEME_LAUNCH = "theme_launch"
    THEME_UPDATE = "theme_update"
    SEASONAL_CAMPAIGN = "seasonal_campaign"
    SYSTEM_RECOVERY = "system_recovery"
    BATCH_CONTENT = "batch_content"


WORKFLOW_DEFINITIONS = {
    WorkflowType.THEME_LAUNCH: {
        "name": "Theme Launch",
        "description": "Full theme launch workflow",
        "steps": [
            {"step_number": 1, "agent": "builder", "action": "create_theme"},
            {"step_number": 2, "agent": "visual_production", "action": "generate_assets"},
            {"step_number": 3, "agent": "platform", "action": "deploy_theme"},
            {"step_number": 4, "agent": "support", "action": "enable_kb", "parallel": True},
            {"step_number": 5, "agent": "marketing", "action": "launch_campaign", "parallel": True},
            {"step_number": 6, "agent": "analytics", "action": "setup_tracking", "parallel": True},
        ],
    },
    WorkflowType.THEME_UPDATE: {
        "name": "Theme Update",
        "description": "Update existing theme",
        "steps": [
            {"step_number": 1, "agent": "builder", "action": "update_theme"},
            {
                "step_number": 2,
                "agent": "visual_production",
                "action": "update_assets",
                "optional": True,
            },
            {"step_number": 3, "agent": "platform", "action": "deploy_update"},
            {"step_number": 4, "agent": "marketing", "action": "update_campaign", "parallel": True},
        ],
    },
    WorkflowType.SEASONAL_CAMPAIGN: {
        "name": "Seasonal Campaign",
        "description": "Seasonal marketing campaign",
        "steps": [
            {"step_number": 1, "agent": "marketing", "action": "create_campaign"},
            {"step_number": 2, "agent": "content", "action": "create_content", "parallel": True},
            {"step_number": 3, "agent": "analytics", "action": "setup_tracking", "parallel": True},
        ],
    },
    WorkflowType.SYSTEM_RECOVERY: {
        "name": "System Recovery",
        "description": "System health check and recovery",
        "steps": [
            {"step_number": 1, "agent": "platform", "action": "health_check"},
            {"step_number": 2, "agent": "platform", "action": "apply_degraded_mode"},
            {"step_number": 3, "agent": "analytics", "action": "generate_recovery_report"},
            {"step_number": 4, "agent": "support", "action": "notify_team"},
        ],
    },
    WorkflowType.BATCH_CONTENT: {
        "name": "Batch Content",
        "description": "Process batch content updates",
        "steps": [
            {"step_number": 1, "agent": "content", "action": "process_batch"},
            {"step_number": 2, "agent": "support", "action": "update_kb"},
        ],
    },
}

WORKFLOW_PRIORITY = {
    WorkflowType.THEME_LAUNCH: 1,
    WorkflowType.THEME_UPDATE: 2,
    WorkflowType.SYSTEM_RECOVERY: 1,
    WorkflowType.SEASONAL_CAMPAIGN: 3,
    WorkflowType.BATCH_CONTENT: 4,
}


def build_workflow_business_key(workflow_type: WorkflowType, context: dict) -> str:
    """Build unique business key for workflow"""
    if workflow_type == WorkflowType.THEME_LAUNCH:
        return f"theme_launch_{context.get('theme_slug', '')}_{context.get('version', '')}"
    elif workflow_type == WorkflowType.THEME_UPDATE:
        return f"theme_update_{context.get('theme_slug', '')}_{context.get('version', '')}"
    elif workflow_type == WorkflowType.SEASONAL_CAMPAIGN:
        return f"campaign_{context.get('season', '')}_{context.get('year', '')}"
    elif workflow_type == WorkflowType.SYSTEM_RECOVERY:
        return "system_recovery"
    elif workflow_type == WorkflowType.BATCH_CONTENT:
        return f"batch_content_{context.get('batch_id', '')}"
    return f"{workflow_type.value}_{context.get('id', '')}"

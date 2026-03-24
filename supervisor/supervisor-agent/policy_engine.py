from typing import Any, Dict, List
from dataclasses import dataclass
from models import WorkflowInstance, WorkflowStatus, ConflictRecord, PolicyRule, AgentHealthRecord

# Default policies
DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    "daily_visual_budget": {
        "type": "budget_limit",
        "rule_type": "budget",
        "active": True,
        "value": 10.00,
        "action": "pause_visual_production",
        "description": "Pause visual production if daily budget exceeded",
    },
    "daily_theme_limit": {
        "type": "limit",
        "rule_type": "limit",
        "active": True,
        "value": 3,
        "action": "block_theme_launch",
        "description": "Block new theme launches if daily limit reached",
    },
    "api_cost_critical": {
        "type": "threshold",
        "rule_type": "api_cost",
        "active": True,
        "value": 100.0,
        "action": "alert_and_pause",
        "description": "Alert and pause when API cost exceeds threshold",
    },
    "quality_threshold": {
        "type": "threshold",
        "rule_type": "quality",
        "active": True,
        "value": 0.70,
        "action": "block_launch",
        "description": "Block theme launch if quality score below threshold",
    },
}

USER_LOCKED_DECISIONS = [
    "pricing",
    "product_deletion",
    "targeting_change",
    "crisis_response",
    "campaign_stop",
    "budget_change",
]


def check_user_locked(domain: str) -> bool:
    """Check if a decision domain is user locked"""
    return domain in USER_LOCKED_DECISIONS


def evaluate_policies(context: Dict[str, Any]) -> List[PolicyRule]:
    """Evaluate all active policies against context"""
    active_policies = []

    for policy_name, policy in DEFAULT_POLICIES.items():
        if not policy.get("active", False):
            continue

        condition_met = False
        rule_type = policy.get("rule_type", "")

        if rule_type == "budget" and "daily_cost" in context:
            if context["daily_cost"] > policy["value"]:
                condition_met = True

        elif rule_type == "limit" and "theme_count" in context:
            if context["theme_count"] >= policy["value"]:
                condition_met = True

        elif rule_type == "api_cost" and "total_api_cost" in context:
            if context["total_api_cost"] > policy["value"]:
                condition_met = True

        elif rule_type == "quality" and "quality_score" in context:
            if context["quality_score"] < policy["value"]:
                condition_met = True

        if condition_met:
            rule = PolicyRule(
                policy_id=policy_name,
                rule_type=rule_type,
                condition=policy,
                action=policy["action"],
                value=policy.get("value"),
                active=True,
            )
            active_policies.append(rule)

    return active_policies


def apply_budget_action(policy: PolicyRule, current_cost: float) -> str:
    """Apply budget-related policy actions"""
    action = policy.action

    if action == "pause_visual_production":
        return "pause_visual_production"
    elif action == "alert_and_pause":
        return "alert_and_pause"
    else:
        return "none"

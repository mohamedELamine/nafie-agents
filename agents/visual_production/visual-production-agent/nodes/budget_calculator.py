from typing import Dict, Any
from ..models import AssetType


class BudgetCalculatorNode:
    def __init__(self, budget_limit: float = 2.00):
        self.budget_limit = budget_limit

    def __call__(self, cost_estimate: float) -> Dict[str, Any]:
        """Calculate budget and reject if exceeded"""
        if cost_estimate > self.budget_limit:
            return {
                "rejected": True,
                "reason": "VISUAL_BUDGET_EXCEEDED",
                "estimated_cost": cost_estimate,
                "budget_limit": self.budget_limit,
            }
        return {
            "rejected": False,
            "estimated_cost": cost_estimate,
            "budget_remaining": self.budget_limit - cost_estimate,
        }


budget_calculator_node = BudgetCalculatorNode(budget_limit=2.00)

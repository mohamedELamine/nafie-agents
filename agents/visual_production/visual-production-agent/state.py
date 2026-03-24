from typing import TypedDict, Optional
from datetime import datetime


class VisualState(TypedDict):
    theme_contract: dict
    batch_id: Optional[str]
    prompt_bundles: dict[str, dict]  # asset_type -> PromptBundle
    generated_assets: list[dict]  # list of GeneratedAsset dicts
    quality_approved: int
    quality_rejected: int
    total_cost: float
    budget_used: float
    review_decision: Optional[str]  # None, "approved", "rejected", "needs_revision"
    review_notes: Optional[str]
    status: str  # "pending", "budget_rejected", "generating", "quality_check", "review_pending", "completed"
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


def make_initial_state(theme_contract: dict, batch_id: str) -> VisualState:
    """Initialize visual state with theme contract"""
    return {
        "theme_contract": theme_contract,
        "batch_id": batch_id,
        "prompt_bundles": {},
        "generated_assets": [],
        "quality_approved": 0,
        "quality_rejected": 0,
        "total_cost": 0.0,
        "budget_used": 0.0,
        "review_decision": None,
        "review_notes": None,
        "status": "pending",
        "started_at": datetime.utcnow(),
        "completed_at": None,
    }

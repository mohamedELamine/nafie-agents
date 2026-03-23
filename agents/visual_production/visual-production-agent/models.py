from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class AssetType(str, Enum):
    HERO_IMAGE = "hero_image"
    PRODUCT_CARD = "product_card"
    SCREENSHOT_HOME = "screenshot_home"
    SCREENSHOT_INNER = "screenshot_inner"
    VIDEO_PREVIEW = "video_preview"


class AssetStatus(str, Enum):
    GENERATING = "generating"
    QUALITY_CHECK = "quality_check"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


@dataclass
class GeneratedAsset:
    asset_id: str
    type: AssetType
    url: str
    dimensions: tuple[int, int]  # (width, height)
    size_kb: float
    quality_score: float  # 0-1
    status: AssetStatus
    generated_at: datetime
    metadata: Optional[dict] = None


@dataclass
class PromptBundle:
    asset_type: AssetType
    positive_prompt: str
    negative_prompt: str
    dimensions: tuple[int, int]
    generator: str  # "flux" or "ideogram"


@dataclass
class AssetManifest:
    batch_id: str
    theme_slug: str
    version: str
    assets: list[GeneratedAsset]
    total_cost: float
    status: str  # "pending", "generating", "review_pending", "review_approved", "published"
    created_at: datetime
    updated_at: datetime
    generated_by: str = "visual_production_agent"
    notes: Optional[str] = None


@dataclass
class BatchStatus:
    batch_id: str
    theme_slug: str
    started_at: datetime
    budget_used: float
    assets_count: int
    status: str  # "pending", "in_progress", "completed", "failed"
    generated_assets: int = 0
    quality_approved: int = 0
    quality_rejected: int = 0

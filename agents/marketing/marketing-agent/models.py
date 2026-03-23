from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketingChannel(str, Enum):
    """Allowed marketing channels for execution."""

    FACEBOOK_PAGE = "facebook_page"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    WHATSAPP_BUSINESS = "whatsapp_business"

    # Channels suggested but not executed
    GOOGLE_ADS = "google_ads"
    META_PAID_ADS = "meta_paid_ads"


class PostFormat(str, Enum):
    """Allowed post formats."""

    FEED_IMAGE = "feed_image"
    FEED_VIDEO = "feed_video"
    REEL = "reel"
    STORY_IMAGE = "story_image"
    STORY_VIDEO = "story_video"
    CAROUSEL = "carousel"
    THREAD = "thread"


class PublishStatus(str, Enum):
    """Publish status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Campaign:
    """Represents a marketing campaign."""

    campaign_id: str
    title: str
    theme_slug: str
    content_snapshot: Dict[str, Any]
    assets_snapshot: Dict[str, Any]
    start_date: datetime
    end_date: datetime
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContentSnapshot:
    """Frozen snapshot of content for a campaign."""

    content_id: str
    campaign_id: str
    content_data: Dict[str, Any]
    snapshot_date: datetime


@dataclass
class AssetSnapshot:
    """Frozen snapshot of assets for a campaign."""

    asset_id: str
    campaign_id: str
    asset_data: Dict[str, Any]
    snapshot_date: datetime


@dataclass
class ScheduledPost:
    """Represents a scheduled post."""

    post_id: str
    campaign_id: str
    channel: MarketingChannel
    format: PostFormat
    scheduled_time: datetime
    content_snapshot_id: str
    asset_snapshot_id: str
    status: PublishStatus = PublishStatus.PENDING
    variant_label: Optional[str] = None
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


@dataclass
class PublishResult:
    """Represents the result of publishing."""

    post_id: str
    success: bool
    message: str
    platform_data: Optional[Dict[str, Any]] = None
    published_at: Optional[datetime] = None


@dataclass
class CampaignLog:
    """Represents a log entry for campaign activities."""

    log_id: str
    campaign_id: str
    event_type: str
    details: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)

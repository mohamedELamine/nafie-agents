from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .models import Campaign, ContentSnapshot, AssetSnapshot, ScheduledPost


class MarketingState(BaseModel):
    """State for marketing workflows."""

    # Campaign data
    current_campaign: Optional[Campaign] = None
    content_snapshot: Optional[ContentSnapshot] = None
    assets_snapshot: Optional[AssetSnapshot] = None

    # Scheduling decisions
    selected_channels: List[str] = []
    selected_formats: List[str] = []
    best_post_time: Optional[datetime] = None
    scheduled_posts: List[ScheduledPost] = []

    # User locked decisions (never modified by agent)
    user_budget: Optional[float] = None
    user_target_audience: Optional[str] = None
    user_campaign_price: Optional[float] = None
    user_campaign_end: Optional[datetime] = None
    user_primary_channel: Optional[str] = None
    user_offer_type: Optional[str] = None

    # Execution status
    readiness_status: str = "pending"
    has_content_ready: bool = False
    has_assets_ready: bool = False
    product_launch_date: Optional[datetime] = None

    # Event tracking
    events: List[Dict[str, Any]] = []
    last_checkpoint: Optional[str] = None
    processing_stats: Dict[str, Any] = {}


def make_initial_state() -> MarketingState:
    """Create initial marketing state."""
    return MarketingState()


def update_state_with_campaign(
    state: MarketingState, campaign: Campaign
) -> MarketingState:
    """Update state with a new campaign."""
    return MarketingState(
        current_campaign=campaign,
        content_snapshot=None,
        assets_snapshot=None,
        selected_channels=[],
        selected_formats=[],
        best_post_time=None,
        scheduled_posts=[],
        readiness_status="pending",
        has_content_ready=False,
        has_assets_ready=False,
        product_launch_date=None,
        events=state.events,
        last_checkpoint=state.last_checkpoint,
        processing_stats=state.processing_stats,
    )


def update_state_with_content(
    state: MarketingState, content: ContentSnapshot
) -> MarketingState:
    """Update state with content snapshot."""
    return MarketingState(
        current_campaign=state.current_campaign,
        content_snapshot=content,
        assets_snapshot=state.assets_snapshot,
        selected_channels=state.selected_channels,
        selected_formats=state.selected_formats,
        best_post_time=state.best_post_time,
        scheduled_posts=state.scheduled_posts,
        readiness_status="pending",
        has_content_ready=True,
        has_assets_ready=state.has_assets_ready,
        product_launch_date=state.product_launch_date,
        events=state.events,
        last_checkpoint=state.last_checkpoint,
        processing_stats=state.processing_stats,
    )


def update_state_with_assets(
    state: MarketingState, assets: AssetSnapshot
) -> MarketingState:
    """Update state with assets snapshot."""
    return MarketingState(
        current_campaign=state.current_campaign,
        content_snapshot=state.content_snapshot,
        assets_snapshot=assets,
        selected_channels=state.selected_channels,
        selected_formats=state.selected_formats,
        best_post_time=state.best_post_time,
        scheduled_posts=state.scheduled_posts,
        readiness_status="pending",
        has_content_ready=state.has_content_ready,
        has_assets_ready=True,
        product_launch_date=state.product_launch_date,
        events=state.events,
        last_checkpoint=state.last_checkpoint,
        processing_stats=state.processing_stats,
    )


def update_state_with_selected_channels(
    state: MarketingState, channels: List[str]
) -> MarketingState:
    """Update state with selected channels."""
    new_channels = list(state.selected_channels)
    for channel in channels:
        if channel not in new_channels:
            new_channels.append(channel)

    return MarketingState(
        current_campaign=state.current_campaign,
        content_snapshot=state.content_snapshot,
        assets_snapshot=state.assets_snapshot,
        selected_channels=new_channels,
        selected_formats=state.selected_formats,
        best_post_time=state.best_post_time,
        scheduled_posts=state.scheduled_posts,
        readiness_status=state.readiness_status,
        has_content_ready=state.has_content_ready,
        has_assets_ready=state.has_assets_ready,
        product_launch_date=state.product_launch_date,
        events=state.events,
        last_checkpoint=state.last_checkpoint,
        processing_stats=state.processing_stats,
    )


def update_state_with_best_post_time(
    state: MarketingState, time: datetime
) -> MarketingState:
    """Update state with best post time."""
    return MarketingState(
        current_campaign=state.current_campaign,
        content_snapshot=state.content_snapshot,
        assets_snapshot=state.assets_snapshot,
        selected_channels=state.selected_channels,
        selected_formats=state.selected_formats,
        best_post_time=time,
        scheduled_posts=state.scheduled_posts,
        readiness_status=state.readiness_status,
        has_content_ready=state.has_content_ready,
        has_assets_ready=state.has_assets_ready,
        product_launch_date=state.product_launch_date,
        events=state.events,
        last_checkpoint=state.last_checkpoint,
        processing_stats=state.processing_stats,
    )

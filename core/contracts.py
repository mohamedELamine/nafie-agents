"""
core/contracts.py
=================
العقود (Contracts) الرسمية بين الوكلاء.
كل حدث يحمل payload يتبع مخطط محدد هنا.
"""

from datetime import datetime, timezone
from typing import TypedDict, Optional, List, Literal, Dict, Any
import uuid


# ══════════════════════════════════════════════════════
# Streams / Channels الموحدة
# ══════════════════════════════════════════════════════

STREAM_THEME_EVENTS = "theme-events"
STREAM_PRODUCT_EVENTS = "product-events"
STREAM_ASSET_EVENTS = "asset-events"
STREAM_SUPPORT_EVENTS = "support-events"
STREAM_MARKETING_EVENTS = "marketing-events"
STREAM_CONTENT_EVENTS = "content-events"
STREAM_BUILDER_EVENTS = "builder-events"
STREAM_ANALYTICS_SIGNALS = "analytics:signals"


# ══════════════════════════════════════════════════════
# أسماء الأحداث المشتركة بين الوكلاء
# ══════════════════════════════════════════════════════

EVENT_THEME_APPROVED = "THEME_APPROVED"
EVENT_THEME_ASSETS_READY = "THEME_ASSETS_READY"
EVENT_THEME_ASSETS_PARTIALLY_READY = "THEME_ASSETS_PARTIALLY_READY"
EVENT_NEW_PRODUCT_LIVE = "NEW_PRODUCT_LIVE"
EVENT_THEME_UPDATED_LIVE = "THEME_UPDATED_LIVE"
EVENT_CONTENT_REQUEST = "CONTENT_REQUEST"
EVENT_CONTENT_READY = "CONTENT_READY"
EVENT_CONTENT_PRODUCED = "CONTENT_PRODUCED"
EVENT_CONTENT_REVIEW_DECIDED = "CONTENT_REVIEW_DECIDED"
EVENT_ANALYTICS_SIGNAL = "ANALYTICS_SIGNAL"
EVENT_CAMPAIGN_LAUNCHED = "CAMPAIGN_LAUNCHED"
EVENT_POST_PUBLISHED = "POST_PUBLISHED"
EVENT_POST_FAILED = "POST_FAILED"
EVENT_POST_SCHEDULED = "POST_SCHEDULED"
EVENT_VISUAL_REVIEW_REQUESTED = "VISUAL_REVIEW_REQUESTED"


# ══════════════════════════════════════════════════════
# عقد THEME_BUILD_REQUESTED (البناء → المنصة)
# ══════════════════════════════════════════════════════

class ThemeBuildRequestedPayload(TypedDict):
    theme_slug:    str
    theme_name_ar: str
    domain:        str
    cluster:       str
    woo_enabled:   bool
    cod_enabled:   bool
    requested_by:  str   # "supervisor" | "platform" | "manual"
    priority:      int


class ThemeBuildCompletedPayload(TypedDict):
    theme_slug:   str
    zip_path:     str
    docs_path:    str
    quality_score: float   # 0.0 – 1.0
    test_results: dict
    decision_log: list
    build_time_sec: int


# ══════════════════════════════════════════════════════
# عقد THEME_PUBLISH_REQUESTED (المنصة)
# ══════════════════════════════════════════════════════

class ThemePublishRequestedPayload(TypedDict):
    theme_slug:    str
    zip_path:      str
    price:         float
    sale_price:    Optional[float]
    categories:    List[str]
    tags:          List[str]
    publish_now:   bool


class ThemePublishedPayload(TypedDict):
    theme_slug:  str
    product_id:  int
    product_url: str
    price:       float


class ThemeApprovedPayload(TypedDict, total=False):
    theme_slug: str
    version: str
    theme_contract: Dict[str, Any]
    package_path: str


class ThemeAssetsReadyPayload(TypedDict, total=False):
    batch_id: str
    theme_slug: str
    idempotency_key: str
    assets: List[Dict[str, Any]]


class NewProductLivePayload(TypedDict, total=False):
    theme_slug: str
    theme_name_ar: str
    version: str
    wp_post_url: str
    ls_product_id: str
    pricing: Dict[str, Any]
    launched_at: str
    theme_contract: Dict[str, Any]


# ══════════════════════════════════════════════════════
# عقد الدعم (Support)
# ══════════════════════════════════════════════════════

class TicketCreatedPayload(TypedDict):
    ticket_id:    str
    customer_id:  str
    theme_slug:   Optional[str]
    subject:      str
    body:         str
    channel:      Literal["email", "chat", "woo_order"]
    language:     Literal["ar", "en"]
    priority:     int


class TicketResolvedPayload(TypedDict):
    ticket_id:       str
    resolution:      str
    resolution_type: Literal["auto", "human", "escalated"]
    satisfaction:    Optional[int]   # 1-5 إن أُعطي


# ══════════════════════════════════════════════════════
# عقد المحتوى (Content)
# ══════════════════════════════════════════════════════

class ContentRequestedPayload(TypedDict):
    content_id:   str
    content_type: Literal[
        "product_description", "blog_post",
        "social_caption", "email_newsletter",
        "seo_meta", "changelog"
    ]
    theme_slug:   Optional[str]
    domain:       Optional[str]
    keywords:     List[str]
    tone:         Literal["formal", "friendly", "technical", "marketing"]
    length:       Literal["short", "medium", "long"]
    requested_by: str


class ContentReadyPayload(TypedDict):
    content_id:   str
    content_type: str
    content_ar:   str
    content_en:   Optional[str]
    seo_score:    Optional[float]
    word_count:   int


class AgentContentReadyPayload(TypedDict, total=False):
    content_id: str
    content_type: str
    theme_slug: Optional[str]
    title: str
    body: str
    variants: Optional[List[Dict[str, str]]]
    metadata: Dict[str, Any]
    validation_score: Optional[float]
    request_id: str
    target_agent: str


# ══════════════════════════════════════════════════════
# عقد التسويق (Marketing)
# ══════════════════════════════════════════════════════

class CampaignTriggeredPayload(TypedDict):
    campaign_id:   str
    campaign_type: Literal["launch", "discount", "newsletter", "social"]
    theme_slug:    Optional[str]
    target_segment: str
    channels:      List[Literal["email", "twitter", "instagram", "telegram"]]


class CampaignLaunchedPayload(TypedDict, total=False):
    campaign_id: str
    theme_slug: Optional[str]
    published_posts: int


class PostPublishedPayload(TypedDict, total=False):
    campaign_id: str
    theme_slug: Optional[str]
    post_id: str
    channel: str
    format: str
    published_at: str


# ══════════════════════════════════════════════════════
# عقد التحليل (Analytics)
# ══════════════════════════════════════════════════════

class ReportRequestedPayload(TypedDict):
    report_id:   str
    report_type: Literal["daily", "weekly", "monthly", "theme", "custom"]
    date_from:   str
    date_to:     str
    metrics:     List[str]


class AnomalyDetectedPayload(TypedDict):
    anomaly_id:    str
    metric:        str
    expected:      float
    actual:        float
    severity:      Literal["low", "medium", "high", "critical"]
    recommendation: str


class AnalyticsSignalPayload(TypedDict, total=False):
    signal_id: str
    signal_type: str
    priority: str
    target_agent: str
    theme_slug: Optional[str]
    data: Dict[str, Any]
    generated_at: str


# ══════════════════════════════════════════════════════
# عقد الإنتاج البصري (Visual Production)
# ══════════════════════════════════════════════════════

class VisualRequestedPayload(TypedDict):
    visual_id:    str
    visual_type:  Literal[
        "theme_screenshot", "social_banner",
        "promo_video", "logo_variations",
        "product_mockup", "demo_images"
    ]
    theme_slug:   Optional[str]
    theme_name_ar: Optional[str]
    domain:       Optional[str]
    aesthetic:    Optional[dict]   # aesthetic_contract من THEME_CONTRACT
    dimensions:   Optional[dict]  # width, height
    count:        int
    requested_by: str


class VisualReadyPayload(TypedDict):
    visual_id:   str
    visual_type: str
    files:       List[str]   # مسارات الملفات
    metadata:    dict


def build_ecosystem_event(
    event_type: str,
    data: Dict[str, Any],
    source: str,
    correlation_id: Optional[str] = None,
    schema_version: str = "1.0",
) -> Dict[str, Any]:
    """Build a shared event envelope for cross-agent stream messages."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "schema_version": schema_version,
        "source": source,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "data": data,
    }

"""
core/contracts.py
=================
العقود (Contracts) الرسمية بين الوكلاء.
كل حدث يحمل payload يتبع مخطط محدد هنا.
"""

from typing import TypedDict, Optional, List, Literal


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


# ══════════════════════════════════════════════════════
# عقد التسويق (Marketing)
# ══════════════════════════════════════════════════════

class CampaignTriggeredPayload(TypedDict):
    campaign_id:   str
    campaign_type: Literal["launch", "discount", "newsletter", "social"]
    theme_slug:    Optional[str]
    target_segment: str
    channels:      List[Literal["email", "twitter", "instagram", "telegram"]]


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

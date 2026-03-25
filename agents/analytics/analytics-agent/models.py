from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalType(str, Enum):
    # Operational — تنبيهات فورية
    NO_OUTPUT_ALERT         = "no_output_alert"
    SALES_DROP_ALERT        = "sales_drop_alert"
    SUPPORT_SURGE_ALERT     = "support_surge_alert"
    CAMPAIGN_NO_OUTPUT      = "campaign_no_output"
    RECURRING_QUALITY_ISSUE = "recurring_quality_issue"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"

    # Business — للوكلاء
    BEST_TIME           = "best_time"
    BEST_CHANNEL        = "best_channel"
    LOW_SALES           = "low_sales"
    HIGH_INTEREST       = "high_interest"
    CAMPAIGN_RESULT     = "campaign_result"
    BEST_VARIANT        = "best_variant"
    CONTENT_PERFORMANCE = "content_performance"
    BEST_CONTENT_TYPE   = "best_content_type"
    PRICING_SIGNAL      = "pricing_signal"
    PRODUCT_SIGNAL      = "product_signal"
    LICENSE_SIGNAL      = "license_signal"
    BUILD_FEEDBACK      = "build_feedback"
    SUPPORT_PATTERN     = "support_pattern"


class SignalPriority(str, Enum):
    IMMEDIATE = "immediate"
    DAILY     = "daily"
    WEEKLY    = "weekly"


class AttributionConfidence(str, Enum):
    HIGH   = "high"    # UTM parameters أو referral token صريح
    MEDIUM = "medium"  # نشر مؤكد + بيع في نافذة 24 ساعة
    LOW    = "low"     # استنتاج من تسلسل النشر — الأكثر شيوعاً


class AttributionChannel(str, Enum):
    FACEBOOK  = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK    = "tiktok"
    EMAIL     = "email"
    WHATSAPP  = "whatsapp"
    DIRECT    = "direct"
    ORGANIC   = "organic"
    UNKNOWN   = "unknown"


class AnalyticsType(str, Enum):
    OPERATIONAL = "operational"  # support surge, quality issues, publish failures
    BUSINESS    = "business"     # sales trend, best channel, stagnant product


@dataclass
class AnalyticsEvent:
    """حدث خام — طبقة Collection"""
    event_id:     str
    event_type:   str
    source_agent: str
    theme_slug:   Optional[str]      # Optional — بعض الأحداث بلا قالب محدد
    raw_data:     Dict[str, Any]
    occurred_at:  datetime           # وقت الحدث الحقيقي — للتحليل
    received_at:  datetime           # وقت الاستلام من Redis — للتشخيص
    processed:    bool = False


@dataclass
class MetricSnapshot:
    """مقياس مُحسَّب — طبقة Metrics"""
    metric_id:    str
    metric_key:   str                # من METRIC_DEFINITIONS
    theme_slug:   Optional[str]
    channel:      Optional[str]
    granularity:  str                # "hour" | "day" | "week" | "month"
    period_start: datetime
    period_end:   datetime
    value:        float
    unit:         str
    computed_at:  datetime


@dataclass
class Pattern:
    """نمط مكتشف — طبقة Pattern Analyzer"""
    pattern_id:         str
    pattern_type:       str
    analytics_type:     AnalyticsType
    theme_slug:         Optional[str]
    channel:            Optional[str]
    description:        str
    confidence:         float
    supporting_metrics: List[str]
    detected_at:        datetime
    is_actionable:      bool


@dataclass
class AnalyticsSignal:
    """إشارة مُولَّدة — طبقة Signal Generator"""
    signal_id:             str
    signal_type:           SignalType
    priority:              SignalPriority
    target_agent:          str
    theme_slug:            Optional[str]
    channel:               Optional[str]
    recommendation:        str
    confidence:            float
    supporting_pattern_id: Optional[str]
    data:                  Dict[str, Any]
    generated_at:          datetime
    sent_at:               Optional[datetime] = None


@dataclass
class AttributionRecord:
    """ربط البيع بمصدره التقريبي"""
    sale_id:               str
    theme_slug:            str
    amount_usd:            float
    license_tier:          str
    channels_touched:      List[AttributionChannel]
    attributed_to:         AttributionChannel
    attribution_model:     str                    # "last_touch_v1"
    attribution_confidence: AttributionConfidence  # دائماً مُعلَن
    attribution_note:      str                    # توضيح ما تم استنتاجه
    sale_date:             datetime               # من occurred_at


@dataclass
class SignalOutcome:
    """نتيجة إشارة — لتحسين الإشارات مستقبلاً"""
    outcome_id:          str
    signal_id:           str
    target_agent:        str
    action_taken:        Optional[str]
    observed_metric:     Optional[str]   # المقياس الذي يُقيّم النتيجة
    before_value:        Optional[float]
    after_value:         Optional[float]
    outcome_window_days: int
    success_score:       Optional[float]  # 0.0 - 1.0
    evaluated_at:        Optional[datetime]
    notes:               Optional[str]


@dataclass
class WeeklyReport:
    """تقرير أسبوعي"""
    report_id:       str
    period_start:    datetime
    period_end:      datetime
    total_sales:     int
    total_revenue:   float
    top_theme:       Optional[str]
    top_channel:     Optional[str]
    support_tickets: int
    escalation_rate: float          # escalated_count / resolved_count
    new_products:    int
    signals_sent:    int
    highlights:      List[str]
    concerns:        List[str]
    generated_at:    datetime

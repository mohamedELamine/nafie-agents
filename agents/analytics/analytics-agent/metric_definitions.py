from typing import Any, Dict, List


METRIC_DEFINITIONS: Dict[str, Dict[str, Any]] = {

    "sales_count": {
        "source":      "lemon_squeezy_api",
        "formula":     "count(orders WHERE status='paid')",
        "granularity": ["hour", "day", "week", "month"],
        "unit":        "count",
        "event_type":  "NEW_SALE",
        "time_field":  "occurred_at",
    },

    "sales_revenue": {
        "source":      "lemon_squeezy_api",
        "formula":     "sum(orders.total_usd WHERE status='paid')",
        "granularity": ["hour", "day", "week", "month"],
        "unit":        "usd",
        "event_type":  "NEW_SALE",
        "time_field":  "occurred_at",
    },

    "sales_by_theme": {
        "source":      "lemon_squeezy_api",
        "formula":     "count(orders) GROUP BY theme_slug",
        "granularity": ["day", "week", "month"],
        "unit":        "count",
        "dimensions":  ["theme_slug"],
        "event_type":  "NEW_SALE",
        "time_field":  "occurred_at",
    },

    "sales_by_channel": {
        "source":      "attribution_records",
        "formula":     "count(attribution_records) GROUP BY attributed_to",
        "granularity": ["day", "week", "month"],
        "unit":        "count",
        "dimensions":  ["attributed_to"],
        "note":        "مبني على Attribution Approximation — LOW confidence الغالب",
    },

    "support_ticket_resolved": {
        "source":      "helpscout_api",
        "formula":     "count(conversations WHERE status='closed')",
        "granularity": ["hour", "day", "week"],
        "unit":        "count",
        "event_type":  "SUPPORT_TICKET_RESOLVED",
        "time_field":  "occurred_at",
    },

    "support_ticket_escalated": {
        "source":      "helpscout_api",
        "formula":     "count(conversations WHERE escalated=True)",
        "granularity": ["hour", "day", "week"],
        "unit":        "count",
        "event_type":  "SUPPORT_TICKET_ESCALATED",
        "time_field":  "occurred_at",
    },

    "support_escalation_rate": {
        "source":      "derived",
        "formula":     "support_ticket_escalated / support_ticket_resolved",
        "granularity": ["day", "week"],
        "unit":        "ratio",
        "note":        "لا تُجمَّع rates — تُحسَّب من الـ counts",
    },

    "support_avg_resolution_minutes": {
        "source":      "helpscout_api",
        "formula":     "avg(conversation.resolved_at - conversation.created_at)",
        "granularity": ["day", "week"],
        "unit":        "minutes",
    },

    "posts_published": {
        "source":      "redis_events",
        "formula":     "count(POST_PUBLISHED events)",
        "granularity": ["hour", "day", "week"],
        "unit":        "count",
        "event_type":  "POST_PUBLISHED",
        "time_field":  "occurred_at",
    },

    "posts_by_channel": {
        "source":      "redis_events",
        "formula":     "count(POST_PUBLISHED) GROUP BY channel",
        "granularity": ["day", "week"],
        "unit":        "count",
        "dimensions":  ["channel"],
        "event_type":  "POST_PUBLISHED",
    },

    "campaign_conversion_rate": {
        "source":      "derived",
        "formula":     "sales_by_channel / posts_by_channel",
        "granularity": ["week", "month"],
        "unit":        "ratio",
        "note":        "تقريبي — Attribution LOW confidence",
    },

    "content_produced": {
        "source":      "redis_events",
        "formula":     "count(CONTENT_PRODUCED events)",
        "granularity": ["day", "week"],
        "unit":        "count",
        "event_type":  "CONTENT_PRODUCED",
        "time_field":  "occurred_at",
    },

    "license_tier_distribution": {
        "source":      "lemon_squeezy_api",
        "formula":     "count(licenses) GROUP BY tier",
        "granularity": ["day", "week", "month"],
        "unit":        "count",
        "dimensions":  ["license_tier"],
    },
}


IMMEDIATE_THRESHOLDS = {
    "no_sales_days":             {"threshold": 30,   "signal": "no_output_alert"},
    "sales_drop_rate":           {"threshold": 0.50, "signal": "sales_drop_alert"},
    "support_surge":             {"threshold": 10,   "signal": "support_surge_alert"},
    "campaign_no_output_hours":  {"threshold": 24,   "signal": "campaign_no_output"},
    "recurring_quality":         {"threshold": 3,    "signal": "recurring_quality_issue"},
}

# Signal → target_agent mapping
SIGNAL_TARGET_MAP = {
    "no_output_alert":         "marketing_agent",
    "sales_drop_alert":        "marketing_agent",
    "support_surge_alert":     "support_agent",
    "campaign_no_output":      "marketing_agent",
    "recurring_quality_issue": "builder_agent",
    "reconciliation_mismatch": "owner",
    "best_time":               "marketing_agent",
    "best_channel":            "marketing_agent",
    "low_sales":               "marketing_agent",
    "campaign_result":         "marketing_agent",
    "content_performance":     "content_agent",
    "best_content_type":       "content_agent",
    "pricing_signal":          "platform_agent",
    "product_signal":          "platform_agent",
    "license_signal":          "platform_agent",
    "build_feedback":          "builder_agent",
    "support_pattern":         "support_agent",
}

ATTRIBUTION_MODEL    = "last_touch_v1"
ATTRIBUTION_WINDOW_DAYS = 7


def get_metric_definition(metric_key: str) -> Dict[str, Any]:
    if metric_key not in METRIC_DEFINITIONS:
        raise ValueError(f"ANL_METRIC_NOT_DEFINED: {metric_key}")
    return METRIC_DEFINITIONS[metric_key]


def get_all_metric_keys() -> List[str]:
    return list(METRIC_DEFINITIONS.keys())


def get_signal_target(signal_type: str) -> str:
    return SIGNAL_TARGET_MAP.get(signal_type, "owner")

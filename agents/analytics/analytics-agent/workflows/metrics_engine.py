"""
Metrics Engine — طبقة ٢
ثلاث وظائف منفصلة بجداول زمنية مستقلة (يُجدولها scheduler.py):
  - metrics_engine_batch()  → كل ساعة (hourly raw metrics)
  - daily_aggregation()     → يومياً 01:00 (hourly → daily)
  - weekly_aggregation()    → أسبوعياً (daily → weekly)

لا إعادة حساب — تجميع فقط. Idempotency على metric_key + granularity + period_start.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..db import event_store, metric_store
from ..db.connection import get_conn
from ..logging_config import get_logger

logger = get_logger("workflows.metrics_engine")


# ── Hourly (كل ساعة) ──────────────────────────────────────────────────────────

def metrics_engine_batch() -> None:
    """
    يُشغَّل كل ساعة — يحسب Hourly metrics للفترة الماضية.
    الفترة = آخر ساعة كاملة (not rolling).
    """
    now          = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    period_start = now - timedelta(hours=1)
    period_end   = now

    logger.info(f"metrics_engine_batch: {period_start.isoformat()} → {period_end.isoformat()}")

    with get_conn() as conn:
        _compute_sales_hourly(conn, period_start, period_end)
        _compute_support_hourly(conn, period_start, period_end)
        _compute_posts_hourly(conn, period_start, period_end)

    logger.info("metrics_engine_batch completed")


def _compute_sales_hourly(conn, period_start: datetime, period_end: datetime) -> None:
    """حساب مقاييس المبيعات للساعة."""
    # idempotency
    if metric_store.snapshot_exists(conn, "sales_count", "hour", period_start):
        logger.debug(f"Hourly sales_count already computed for {period_start} — skip")
        return

    events = event_store.get_events(
        conn,
        event_type = "NEW_SALE",
        since      = period_start,
        before     = period_end,
    )

    count   = len(events)
    revenue = sum(float(e.get("raw_data", {}).get("amount_usd", 0)) for e in events)

    _save_metric(conn, "sales_count",   "hour", period_start, period_end, float(count),   "count")
    _save_metric(conn, "sales_revenue", "hour", period_start, period_end, revenue,         "usd")

    # مجمَّع حسب القالب
    by_theme: Dict[str, float] = {}
    for e in events:
        slug = e.get("theme_slug") or "unknown"
        by_theme[slug] = by_theme.get(slug, 0) + 1

    for theme_slug, cnt in by_theme.items():
        _save_metric(
            conn, "sales_by_theme", "hour", period_start, period_end,
            float(cnt), "count", theme_slug=theme_slug,
        )


def _compute_support_hourly(conn, period_start: datetime, period_end: datetime) -> None:
    """حساب تذاكر الدعم للساعة."""
    if metric_store.snapshot_exists(conn, "support_ticket_resolved", "hour", period_start):
        return

    resolved   = event_store.get_events(conn, "SUPPORT_TICKET_RESOLVED",  since=period_start, before=period_end)
    escalated  = event_store.get_events(conn, "SUPPORT_TICKET_ESCALATED", since=period_start, before=period_end)

    _save_metric(conn, "support_ticket_resolved",  "hour", period_start, period_end, float(len(resolved)),  "count")
    _save_metric(conn, "support_ticket_escalated", "hour", period_start, period_end, float(len(escalated)), "count")


def _compute_posts_hourly(conn, period_start: datetime, period_end: datetime) -> None:
    """حساب المنشورات للساعة."""
    if metric_store.snapshot_exists(conn, "posts_published", "hour", period_start):
        return

    posts = event_store.get_events(conn, "POST_PUBLISHED", since=period_start, before=period_end)
    _save_metric(conn, "posts_published", "hour", period_start, period_end, float(len(posts)), "count")

    by_channel: Dict[str, float] = {}
    for p in posts:
        ch = p.get("raw_data", {}).get("channel", "unknown")
        by_channel[ch] = by_channel.get(ch, 0) + 1

    for channel, cnt in by_channel.items():
        _save_metric(
            conn, "posts_by_channel", "hour", period_start, period_end,
            float(cnt), "count", channel=channel,
        )


# ── Daily (يومياً 01:00) ─────────────────────────────────────────────────────

def daily_aggregation() -> None:
    """
    يُشغَّل يومياً 01:00 — يجمّع hourly → daily.
    لا إعادة حساب — تجميع بالـ SUM من hourly snapshots.
    """
    yesterday_start = (datetime.utcnow() - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday_end = yesterday_start + timedelta(days=1)

    logger.info(f"daily_aggregation: {yesterday_start.date()}")

    daily_metrics = [
        ("sales_count",   "day", "count"),
        ("sales_revenue", "day", "usd"),
        ("posts_published", "day", "count"),
        ("support_ticket_resolved",  "day", "count"),
        ("support_ticket_escalated", "day", "count"),
    ]

    with get_conn() as conn:
        for metric_key, granularity, unit in daily_metrics:
            if metric_store.snapshot_exists(conn, metric_key, granularity, yesterday_start):
                logger.debug(f"Daily {metric_key} already aggregated — skip")
                continue

            hourly_sum = metric_store.sum_snapshots(
                conn,
                metric_key   = metric_key,
                granularity  = "hour",
                period_start = yesterday_start,
                period_end   = yesterday_end,
            )
            _save_metric(conn, metric_key, granularity, yesterday_start, yesterday_end, hourly_sum, unit)

        # escalation_rate = derived (لا تُجمَّع — تُحسَّب من counts)
        resolved  = metric_store.sum_snapshots(conn, "support_ticket_resolved",  "hour", yesterday_start, yesterday_end)
        escalated = metric_store.sum_snapshots(conn, "support_ticket_escalated", "hour", yesterday_start, yesterday_end)
        if resolved > 0 and not metric_store.snapshot_exists(conn, "support_escalation_rate", "day", yesterday_start):
            rate = escalated / resolved
            _save_metric(conn, "support_escalation_rate", "day", yesterday_start, yesterday_end, rate, "ratio")

        # تجميع by_theme يومياً
        _aggregate_by_theme_daily(conn, yesterday_start, yesterday_end)

    logger.info("daily_aggregation completed")


def _aggregate_by_theme_daily(conn, period_start: datetime, period_end: datetime) -> None:
    """تجميع المبيعات حسب القالب يومياً."""
    hourly_snapshots = metric_store.get_snapshots_by_key(
        conn,
        metric_key   = "sales_by_theme",
        granularity  = "hour",
        period_start = period_start,
        period_end   = period_end,
    )

    by_theme: Dict[str, float] = {}
    for snap in hourly_snapshots:
        slug = snap.get("theme_slug") or "unknown"
        by_theme[slug] = by_theme.get(slug, 0) + float(snap.get("value", 0))

    for theme_slug, cnt in by_theme.items():
        if not metric_store.snapshot_exists(conn, "sales_by_theme", "day", period_start, theme_slug=theme_slug):
            _save_metric(
                conn, "sales_by_theme", "day", period_start, period_end,
                cnt, "count", theme_slug=theme_slug,
            )


# ── Weekly (أسبوعياً) ────────────────────────────────────────────────────────

def weekly_aggregation() -> None:
    """
    يُشغَّل أسبوعياً — يجمّع daily → weekly.
    يحسب أسبوع كامل (الاثنين → الأحد).
    """
    today        = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_end     = today
    week_start   = today - timedelta(days=7)

    logger.info(f"weekly_aggregation: {week_start.date()} → {week_end.date()}")

    weekly_metrics = [
        ("sales_count",   "week", "count"),
        ("sales_revenue", "week", "usd"),
        ("posts_published", "week", "count"),
        ("support_ticket_resolved",  "week", "count"),
        ("support_ticket_escalated", "week", "count"),
    ]

    with get_conn() as conn:
        for metric_key, granularity, unit in weekly_metrics:
            if metric_store.snapshot_exists(conn, metric_key, granularity, week_start):
                logger.debug(f"Weekly {metric_key} already aggregated — skip")
                continue

            daily_sum = metric_store.sum_snapshots(
                conn,
                metric_key   = metric_key,
                granularity  = "day",
                period_start = week_start,
                period_end   = week_end,
            )
            _save_metric(conn, metric_key, granularity, week_start, week_end, daily_sum, unit)

        # escalation_rate أسبوعي
        resolved  = metric_store.sum_snapshots(conn, "support_ticket_resolved",  "day", week_start, week_end)
        escalated = metric_store.sum_snapshots(conn, "support_ticket_escalated", "day", week_start, week_end)
        if resolved > 0 and not metric_store.snapshot_exists(conn, "support_escalation_rate", "week", week_start):
            rate = escalated / resolved
            _save_metric(conn, "support_escalation_rate", "week", week_start, week_end, rate, "ratio")

    logger.info("weekly_aggregation completed")


# ── Helper ────────────────────────────────────────────────────────────────────

def _save_metric(
    conn,
    metric_key:   str,
    granularity:  str,
    period_start: datetime,
    period_end:   datetime,
    value:        float,
    unit:         str,
    theme_slug:   Optional[str] = None,
    channel:      Optional[str] = None,
) -> None:
    metric_store.save_snapshot(
        conn,
        metric_id    = str(uuid.uuid4()),
        metric_key   = metric_key,
        theme_slug   = theme_slug,
        channel      = channel,
        granularity  = granularity,
        period_start = period_start,
        period_end   = period_end,
        value        = value,
        unit         = unit,
    )

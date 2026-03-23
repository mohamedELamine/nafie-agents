from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .models import AnalyticsEvent, AttributionConfidence, SignalType


class AnalyticsState(BaseModel):
    """State for analytics workflows."""

    events: List[AnalyticsEvent] = []
    metrics: Dict[str, Any] = {}
    patterns: List[Any] = []
    signals: List[Any] = []
    attribution_records: List[Any] = []
    weekly_reports: List[Any] = []
    signal_outcomes: List[Any] = []
    last_evaluated: Optional[datetime] = None
    processing_stats: Dict[str, Any] = {}


def make_initial_state() -> AnalyticsState:
    """Create initial analytics state."""
    return AnalyticsState()


def update_state_with_event(
    state: AnalyticsState, event: AnalyticsEvent
) -> AnalyticsState:
    """Update state with a new event."""
    return AnalyticsState(
        events=state.events + [event],
        metrics=state.metrics,
        patterns=state.patterns,
        signals=state.signals,
        attribution_records=state.attribution_records,
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes,
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )


def update_state_with_metric(
    state: AnalyticsState,
    metric_key: str,
    value: float,
    period_start: datetime,
    period_end: datetime,
    theme_slug: str,
    channel: Optional[str] = None,
) -> AnalyticsState:
    """Update state with a new metric snapshot."""
    from .models import MetricSnapshot

    metric = MetricSnapshot(
        metric_id=f"metric_{metric_key}_{period_start.isoformat()}",
        metric_key=metric_key,
        theme_slug=theme_slug,
        channel=channel,
        granularity="day",
        period_start=period_start,
        period_end=period_end,
        value=value,
        unit="count"
        if "count" in metric_key or "sales" in metric_key.lower()
        else "usd",
        computed_at=datetime.utcnow(),
    )

    new_metrics = dict(state.metrics)
    new_metrics[metric_key] = metric

    return AnalyticsState(
        events=state.events,
        metrics=new_metrics,
        patterns=state.patterns,
        signals=state.signals,
        attribution_records=state.attribution_records,
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes,
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )


def update_state_with_pattern(state: AnalyticsState, pattern: Any) -> AnalyticsState:
    """Update state with a new pattern."""
    return AnalyticsState(
        events=state.events,
        metrics=state.metrics,
        patterns=state.patterns + [pattern],
        signals=state.signals,
        attribution_records=state.attribution_records,
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes,
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )


def update_state_with_signal(state: AnalyticsState, signal: Any) -> AnalyticsState:
    """Update state with a new signal."""
    return AnalyticsState(
        events=state.events,
        metrics=state.metrics,
        patterns=state.patterns,
        signals=state.signals + [signal],
        attribution_records=state.attribution_records,
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes,
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )


def update_state_with_attribution(
    state: AnalyticsState, attribution: Any
) -> AnalyticsState:
    """Update state with a new attribution record."""
    return AnalyticsState(
        events=state.events,
        metrics=state.metrics,
        patterns=state.patterns,
        signals=state.signals,
        attribution_records=state.attribution_records + [attribution],
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes,
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )


def update_state_with_outcome(state: AnalyticsState, outcome: Any) -> AnalyticsState:
    """Update state with a new signal outcome."""
    return AnalyticsState(
        events=state.events,
        metrics=state.metrics,
        patterns=state.patterns,
        signals=state.signals,
        attribution_records=state.attribution_records,
        weekly_reports=state.weekly_reports,
        signal_outcomes=state.signal_outcomes + [outcome],
        last_evaluated=state.last_evaluated,
        processing_stats=state.processing_stats,
    )

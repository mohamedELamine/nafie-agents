from .event_store import (
    save_event,
    event_exists,
    count_events,
    get_last_event,
    get_events,
    backfill_sale,
    get_events_by_type,
)

from .metric_store import (
    save_snapshot,
    get_snapshot,
    sum_metrics,
    aggregate_hourly_to_daily,
    get_period_metrics,
    snapshot_exists,
    sum_snapshots,
    get_snapshots_by_key,
)

from .signal_store import (
    save_signal,
    signal_sent_recently,
    mark_signal_sent,
    get_signals_by_type,
    get_signals_filtered,
)

from .attribution_store import (
    save_record,
    get_records_by_theme,
    get_records_by_channel,
    get_attribution_summary,
)

from .pattern_store import (
    save_pattern,
    get_recent_patterns,
    get_patterns_by_type,
)

from .report_store import (
    save_report,
    get_report,
    get_latest_report,
)

from .outcome_store import (
    save_outcome,
    get_outcome,
    get_outcomes_by_signal,
    get_signal_outcome_summary,
)

__all__ = [
    # Event store
    "save_event",
    "event_exists",
    "count_events",
    "get_last_event",
    "get_events",
    "backfill_sale",
    "get_events_by_type",
    # Metric store
    "save_snapshot",
    "get_snapshot",
    "sum_metrics",
    "aggregate_hourly_to_daily",
    "get_period_metrics",
    "snapshot_exists",
    "sum_snapshots",
    "get_snapshots_by_key",
    # Signal store
    "save_signal",
    "signal_sent_recently",
    "mark_signal_sent",
    "get_signals_by_type",
    "get_signals_filtered",
    # Attribution store
    "save_record",
    "get_records_by_theme",
    "get_records_by_channel",
    "get_attribution_summary",
    # Pattern store
    "save_pattern",
    "get_recent_patterns",
    "get_patterns_by_type",
    # Report store
    "save_report",
    "get_report",
    "get_latest_report",
    # Outcome store
    "save_outcome",
    "get_outcome",
    "get_outcomes_by_signal",
    "get_signal_outcome_summary",
]

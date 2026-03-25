from datetime import datetime, timezone
from typing import Any, Dict, List

from ..services.redis_bus import RedisBus
from ..state import (
    MarketingState,
    update_state_with_best_post_time,
    update_state_with_selected_channels,
)
from ..logging_config import get_logger

logger = get_logger("nodes.analytics_consumer")

# Signal types the agent may apply autonomously (USER_LOCKED_DECISIONS excluded)
# Must match AnalyticsSignalType.value from analytics-agent/models.py
AUTO_APPLICABLE_SIGNALS = {"best_time", "best_channel"}


def _update_state_with_formats(state: MarketingState, formats: List[str]) -> MarketingState:
    """Return a copy of state with new formats merged in."""
    new_formats = list(state.selected_formats)
    for fmt in formats:
        if fmt not in new_formats:
            new_formats.append(fmt)

    return MarketingState(
        current_campaign      = state.current_campaign,
        content_snapshot      = state.content_snapshot,
        assets_snapshot       = state.assets_snapshot,
        selected_channels     = state.selected_channels,
        selected_formats      = new_formats,
        best_post_time        = state.best_post_time,
        scheduled_posts       = state.scheduled_posts,
        readiness_status      = state.readiness_status,
        has_content_ready     = state.has_content_ready,
        has_assets_ready      = state.has_assets_ready,
        product_launch_date   = state.product_launch_date,
        events                = state.events,
        last_checkpoint       = state.last_checkpoint,
        processing_stats      = state.processing_stats,
    )


def make_analytics_consumer_node(redis: RedisBus) -> callable:
    """Create the analytics consumer node."""

    def analytics_consumer_node(state: MarketingState) -> Dict[str, Any]:
        """Consume AUTO_APPLICABLE_SIGNALS from the analytics agent stream."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning no data")
                return {
                    "applied_signals": [],
                    "user_locked_decisions_unchanged": True,
                }

            signals = redis.read_group(
                stream        = "analytics:signals",
                consumer_name = "marketing-analytics-consumer",
                count         = 10,
                block_ms      = 1000,
                min_id        = ">",
            )

            applied_signals: List[Dict[str, Any]] = []

            for signal in signals:
                message_id  = signal.pop("__message_id", None)
                signal_type = signal.get("signal_type", "")
                data        = signal.get("data", {})

                if signal_type not in AUTO_APPLICABLE_SIGNALS:
                    # Acknowledge unsupported signals without acting on them
                    if message_id:
                        redis.ack("analytics:signals", message_id)
                    continue

                logger.info(
                    f"Applying AUTO_APPLICABLE_SIGNAL: {signal_type} "
                    f"for campaign {state.current_campaign.campaign_id}"
                )

                applied_signals.append({
                    "signal_type": signal_type,
                    "data":        data,
                    "applied_at":  datetime.now(timezone.utc).isoformat(),
                })

                if signal_type == "best_time" and "best_time" in data:
                    try:
                        best_time = datetime.fromisoformat(data["best_time"])
                        state = update_state_with_best_post_time(state, best_time)
                    except Exception as exc:
                        logger.error(f"Error applying best_time signal: {exc}")

                elif signal_type == "best_channel" and "best_channel" in data:
                    channel = data["best_channel"]
                    channels = channel if isinstance(channel, list) else [channel]
                    state = update_state_with_selected_channels(state, channels)

                if message_id:
                    redis.ack("analytics:signals", message_id)

            logger.info(
                f"Analytics consumer processed {len(applied_signals)} signals for "
                f"campaign {state.current_campaign.campaign_id}"
            )

            return {
                "applied_signals":                applied_signals,
                "user_locked_decisions_unchanged": True,
            }

        except Exception as e:
            logger.error(f"Error in analytics_consumer_node: {e}")
            return {
                "applied_signals":                [],
                "user_locked_decisions_unchanged": True,
            }

    return analytics_consumer_node

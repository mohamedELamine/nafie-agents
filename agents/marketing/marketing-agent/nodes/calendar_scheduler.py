from datetime import datetime, timedelta
from typing import Any, Dict

from ..db import marketing_calendar
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..state import MarketingState

logger = get_logger("nodes.calendar_scheduler")


def make_calendar_scheduler_node(redis) -> callable:
    """Create the calendar scheduler node."""

    def calendar_scheduler_node(state: MarketingState) -> Dict[str, Any]:
        """Schedule posts in the marketing calendar."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning error")
                return {"success": False, "reason": "no_campaign"}

            # Get channel and format selections from state
            autonomous_channels = list(getattr(state, "selected_channels", []))
            formats             = list(getattr(state, "selected_formats", []))
            best_time           = state.best_post_time

            if not autonomous_channels:
                logger.warning("No autonomous channels selected")
                return {"success": False, "reason": "no_channels_selected"}

            if not formats:
                logger.warning("No formats selected — defaulting to feed_image")
                formats = ["feed_image"]

            # Use best time if available, otherwise current time + 1 hour
            scheduled_time = best_time if best_time else datetime.utcnow() + timedelta(hours=1)

            scheduled_posts = []
            variant_count   = 1

            with get_conn() as conn:
                for channel in autonomous_channels:
                    for post_format in formats:
                        # post_format is a string (from state.selected_formats)
                        fmt_str = post_format if isinstance(post_format, str) else post_format.value
                        post_id = (
                            f"post_{state.current_campaign.campaign_id}"
                            f"_{channel}_{fmt_str}_{variant_count}"
                        )

                        post_data = {
                            "post_id":              post_id,
                            "campaign_id":          state.current_campaign.campaign_id,
                            "channel":              channel,
                            "format":               fmt_str,
                            "scheduled_time":       scheduled_time,
                            "content_snapshot_id":  state.content_snapshot.content_id
                                                    if state.content_snapshot else "",
                            "asset_snapshot_id":    state.assets_snapshot.asset_id
                                                    if state.assets_snapshot else "",
                            "status":               "scheduled",
                            "variant_label":        str(variant_count),
                        }

                        marketing_calendar.schedule_post(conn, post_data)
                        scheduled_posts.append(post_data)
                        variant_count += 1

            # Create Redis checkpoint (TTL = 72 h, as per constitution)
            checkpoint_data = {
                "campaign_id":        state.current_campaign.campaign_id,
                "scheduled_posts":    len(scheduled_posts),
                "scheduled_time":     scheduled_time.isoformat(),
                "autonomous_channels": autonomous_channels,
                "formats":            formats,
            }
            checkpoint_id = redis.create_checkpoint(
                state.current_campaign.campaign_id,
                checkpoint_data,
            )

            logger.info(
                f"Scheduled {len(scheduled_posts)} posts for campaign "
                f"{state.current_campaign.campaign_id} at {scheduled_time.isoformat()}"
            )

            return {
                "success":              True,
                "checkpoint_id":        checkpoint_id,
                "scheduled_posts_count": len(scheduled_posts),
            }

        except Exception as e:
            logger.error(f"Error in calendar_scheduler_node: {e}")
            return {"success": False, "reason": f"error: {str(e)}"}

    return calendar_scheduler_node

from datetime import datetime, timezone
from typing import Any, Dict

from ..db import marketing_calendar, campaign_log
from ..db.connection import get_conn
from ..logging_config import get_logger

logger = get_logger("nodes.rejection_handler")


def make_rejection_handler_node(resend_client) -> callable:
    """Create the rejection handler node."""

    def rejection_handler_node(state: Any) -> Dict[str, Any]:
        """Handle publish failures — log, notify, and mark for retry."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning no errors")
                return {
                    "has_failures": False,
                    "failed_posts": [],
                    "route_after_rejection": "retry",
                }

            with get_conn() as conn:
                failed_posts = marketing_calendar.get_scheduled_posts(
                    conn,
                    campaign_id=state.current_campaign.campaign_id,
                    status="failed",
                    limit=10,
                )

                if not failed_posts:
                    logger.info("No failed posts for campaign")
                    return {
                        "has_failures": False,
                        "failed_posts": [],
                        "route_after_rejection": "campaign_recorder",
                    }

                logger.warning(
                    f"Handling {len(failed_posts)} failed posts for campaign "
                    f"{state.current_campaign.campaign_id}"
                )

                for post in failed_posts:
                    post_id        = post["post_id"]
                    channel        = post["channel"]
                    failure_reason = post.get("failure_reason", "Unknown error")

                    # Log the failure
                    log_entry = {
                        "log_id":      f"log_{post_id}_{int(datetime.now(timezone.utc).timestamp())}",
                        "campaign_id": state.current_campaign.campaign_id,
                        "event_type":  "PUBLISH_FAILED",
                        "details": {
                            "post_id":        post_id,
                            "channel":        channel,
                            "failure_reason": failure_reason,
                        },
                    }
                    campaign_log.save_log(conn, log_entry)

                    # Notify via Resend
                    try:
                        resend_client.send_publish_failed(
                            post_id    = post_id,
                            campaign_id = state.current_campaign.campaign_id,
                            channel    = channel,
                            error      = failure_reason,
                        )
                    except Exception as notify_err:
                        logger.error(f"Error sending failure notification: {notify_err}")

            return {
                "has_failures": True,
                "failed_posts": [
                    {
                        "post_id":        p["post_id"],
                        "channel":        p["channel"],
                        "failure_reason": p.get("failure_reason"),
                    }
                    for p in failed_posts
                ],
                "route_after_rejection": "retry",
            }

        except Exception as e:
            logger.error(f"Error in rejection_handler_node: {e}")
            return {
                "has_failures": False,
                "failed_posts": [],
                "route_after_rejection": "campaign_recorder",
            }

    return rejection_handler_node

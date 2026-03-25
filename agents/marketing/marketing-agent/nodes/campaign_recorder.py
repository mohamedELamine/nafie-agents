from datetime import datetime, timezone
from typing import Any, Dict

from core.contracts import (
    EVENT_CAMPAIGN_LAUNCHED,
    EVENT_POST_PUBLISHED,
    STREAM_MARKETING_EVENTS,
)
from ..db import marketing_calendar, campaign_log
from ..db.connection import get_conn
from ..services.redis_bus import RedisBus
from ..logging_config import get_logger

logger = get_logger("nodes.campaign_recorder")


def make_campaign_recorder_node(redis: RedisBus) -> callable:
    """Create the campaign recorder node."""

    def campaign_recorder_node(state: Any) -> Dict[str, Any]:
        """Record campaign results and emit outbound events."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning no events")
                return {
                    "has_events": False,
                    "events": [],
                    "route_after_campaign": "readiness_aggregator",
                }

            events = []

            with get_conn() as conn:
                scheduled_posts = marketing_calendar.get_scheduled_posts(
                    conn,
                    campaign_id=state.current_campaign.campaign_id,
                    limit=100,
                )

                for post in scheduled_posts:
                    post_id = post["post_id"]
                    status  = post.get("status", "scheduled")

                    if status == "published":
                        event = {
                            "log_id":      f"log_{post_id}_published_{int(datetime.now(timezone.utc).timestamp())}",
                            "campaign_id": state.current_campaign.campaign_id,
                            "event_type":  "POST_PUBLISHED",
                            "details": {
                                "post_id":      post_id,
                                "channel":      post["channel"],
                                "format":       post["format"],
                                "published_at": (
                                    post["published_at"].isoformat()
                                    if post.get("published_at")
                                    else datetime.now(timezone.utc).isoformat()
                                ),
                            },
                        }
                    elif status == "failed":
                        event = {
                            "log_id":      f"log_{post_id}_failed_{int(datetime.now(timezone.utc).timestamp())}",
                            "campaign_id": state.current_campaign.campaign_id,
                            "event_type":  "POST_FAILED",
                            "details": {
                                "post_id":        post_id,
                                "channel":        post["channel"],
                                "format":         post["format"],
                                "failure_reason": post.get("failure_reason"),
                            },
                        }
                    else:
                        event = {
                            "log_id":      f"log_{post_id}_scheduled_{int(datetime.now(timezone.utc).timestamp())}",
                            "campaign_id": state.current_campaign.campaign_id,
                            "event_type":  "POST_SCHEDULED",
                            "details": {
                                "post_id":        post_id,
                                "channel":        post["channel"],
                                "format":         post["format"],
                                "scheduled_time": post["scheduled_time"].isoformat(),
                            },
                        }

                    campaign_log.save_log(conn, event)
                    events.append(event)

                    if status == "published":
                        redis.publish_stream(
                            STREAM_MARKETING_EVENTS,
                            redis.build_event(
                                event_type=EVENT_POST_PUBLISHED,
                                campaign_id=state.current_campaign.campaign_id,
                                theme_slug=state.current_campaign.theme_slug,
                                data=event["details"],
                            ),
                        )

                # Determine final campaign status
                published = sum(1 for p in scheduled_posts if p.get("status") == "published")
                failed    = sum(1 for p in scheduled_posts if p.get("status") == "failed")
                scheduled = len(scheduled_posts) - published - failed

                if scheduled == 0 and scheduled_posts:
                    if published > 0 and failed == 0:
                        final_status = "completed"
                    elif failed > 0 and published == 0:
                        final_status = "failed"
                    else:
                        final_status = "in_progress"

                    marketing_calendar.save_campaign(
                        conn,
                        {
                            "campaign_id":      state.current_campaign.campaign_id,
                            "title":            state.current_campaign.title,
                            "theme_slug":       state.current_campaign.theme_slug,
                            "content_snapshot": {},
                            "assets_snapshot":  {},
                            "start_date":       state.current_campaign.start_date,
                            "end_date":         state.current_campaign.end_date,
                            "status":           final_status,
                        },
                    )

            # Emit CAMPAIGN_LAUNCHED to Redis if any post was published
            published_events = [e for e in events if e["event_type"] == "POST_PUBLISHED"]
            if published_events:
                redis.publish_stream(
                    STREAM_MARKETING_EVENTS,
                    redis.build_event(
                        event_type=EVENT_CAMPAIGN_LAUNCHED,
                        campaign_id=state.current_campaign.campaign_id,
                        theme_slug=state.current_campaign.theme_slug,
                        data={"published_posts": len(published_events)},
                    ),
                )

            logger.info(
                f"Campaign recorder processed {len(events)} events for campaign "
                f"{state.current_campaign.campaign_id}"
            )

            return {
                "has_events":            len(events) > 0,
                "events":                events,
                "route_after_campaign":  "readiness_aggregator",
            }

        except Exception as e:
            logger.error(f"Error in campaign_recorder_node: {e}")
            return {
                "has_events":           False,
                "events":               [],
                "route_after_campaign": "readiness_aggregator",
            }

    return campaign_recorder_node

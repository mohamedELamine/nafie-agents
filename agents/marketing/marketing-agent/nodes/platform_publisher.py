from typing import Any, Dict

from ..db import marketing_calendar
from ..db.connection import get_conn
from ..logging_config import get_logger

logger = get_logger("nodes.platform_publisher")


def make_platform_publisher_node(facebook, instagram, tiktok, whatsapp) -> callable:
    """Create the platform publisher node."""

    def _publish_post(post: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a single post to the appropriate platform (sync)."""
        post_id      = post["post_id"]
        channel      = post["channel"]
        post_format  = post["format"]

        logger.info(f"Publishing post {post_id} to channel {channel}")

        result: Dict[str, Any] = {"post_id": post_id, "channel": channel, "success": False}

        try:
            if channel == "facebook_page":
                if post_format in ["feed_image", "feed_video"]:
                    page_id   = post.get("page_id", "")
                    message   = post.get("message", "")
                    media_url = post.get("media_url")
                    if page_id and media_url:
                        media_type = "VIDEO" if post_format == "feed_video" else "IMAGE"
                        result = facebook.post_to_page(
                            page_id=page_id,
                            message=message,
                            media_url=media_url,
                            media_type=media_type,
                        )
                    else:
                        result["error"] = "Missing page_id or media_url"

            elif channel == "instagram":
                if post_format in ["feed_image", "reel"]:
                    media_id = post.get("media_id", "")
                    caption  = post.get("caption", "")
                    if media_id:
                        if post_format == "reel":
                            result = instagram.post_reel(media_id=media_id, caption=caption)
                        else:
                            result = instagram.post_feed_image(media_id=media_id, caption=caption)
                    else:
                        result["error"] = "Missing media_id"

            elif channel == "tiktok":
                if post_format in ["video", "feed_video"]:
                    video_url   = post.get("video_url", "")
                    description = post.get("description", "")
                    tags        = post.get("tags", [])
                    if video_url:
                        result = tiktok.post_video(
                            video_url=video_url,
                            description=description,
                            tags=tags,
                        )
                    else:
                        result["error"] = "Missing video_url"

            elif channel == "whatsapp_business":
                recipient     = post.get("recipient", "")
                template_name = post.get("template_name", "")
                if recipient and template_name:
                    result = whatsapp.send_broadcast_template(
                        recipient=recipient,
                        template_name=template_name,
                    )
                else:
                    result["error"] = "Missing recipient or template_name"

            else:
                result["error"] = f"Unsupported channel: {channel}"

        except Exception as exc:
            logger.error(f"Error publishing post {post_id}: {exc}")
            result["error"] = str(exc)

        return result

    def platform_publisher_node(state: Any) -> Dict[str, Any]:
        """Publish to all autonomous channels."""
        try:
            if not state.current_campaign:
                logger.warning("No current campaign, returning error")
                return {"success": False, "reason": "no_campaign"}

            with get_conn() as conn:
                scheduled_posts = marketing_calendar.get_scheduled_posts(
                    conn,
                    campaign_id=state.current_campaign.campaign_id,
                    status="scheduled",
                    limit=10,
                )

                if not scheduled_posts:
                    logger.warning("No scheduled posts found")
                    return {"success": False, "reason": "no_scheduled_posts"}

                results = [_publish_post(post) for post in scheduled_posts]

                for result in results:
                    if result.get("success"):
                        logger.info(f"Published post: {result.get('post_id')}")
                        marketing_calendar.mark_published(conn, result["post_id"])
                    else:
                        error = result.get("error", "Unknown error")
                        logger.error(f"Failed post {result.get('post_id')}: {error}")
                        marketing_calendar.mark_failed(conn, result["post_id"], error)

            successful = sum(1 for r in results if r.get("success"))
            failed     = len(results) - successful

            logger.info(
                f"Platform publisher done: {successful} success, {failed} failed"
            )

            return {
                "success": True,
                "published_count": successful,
                "failed_count": failed,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error in platform_publisher_node: {e}")
            return {"success": False, "reason": f"error: {str(e)}"}

    return platform_publisher_node

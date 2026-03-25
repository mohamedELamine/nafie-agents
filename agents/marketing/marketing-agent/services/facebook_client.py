from typing import Any, Dict, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.facebook_client")


class FacebookClient:
    """Client for Facebook Graph API."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, page_token: str):
        self.page_token = page_token
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {page_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def post_to_page(
        self,
        page_id: str,
        message: str,
        media_url: Optional[str] = None,
        media_type: str = "IMAGE",
    ) -> Dict[str, Any]:
        """Post a message to Facebook page."""
        try:
            endpoint = f"{self.BASE_URL}/{page_id}/feed"

            payload: Dict[str, Any] = {
                "message": message,
            }

            if media_url:
                payload["attached_media"] = [{"media_fbid": media_url}]

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(
                f"Posted to Facebook page {page_id}: {data.get('id', 'unknown')}"
            )
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Error posting to Facebook page: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error posting to Facebook: {e}")
            return {"success": False, "error": str(e)}

    def post_story(
        self,
        page_id: str,
        media_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a story to Facebook page."""
        try:
            # First upload media
            media_endpoint = f"{self.BASE_URL}/{page_id}/photos"

            with httpx.Client(
                headers={"Authorization": f"Bearer {self.page_token}"},
                timeout=60.0,
            ) as upload_client:
                media_response = upload_client.post(
                    media_endpoint,
                    files={"source": open(media_url, "rb")},
                    params={"caption": caption or ""},
                )
                media_response.raise_for_status()
                media_data = media_response.json()
                media_fbid = media_data.get("id")

            if not media_fbid:
                return {"success": False, "error": "Failed to upload media"}

            # Then create story
            story_endpoint = f"{self.BASE_URL}/{page_id}/stories"
            story_response = self.client.post(
                story_endpoint,
                json={"media_url": media_fbid},
            )
            story_response.raise_for_status()

            story_data = story_response.json()
            logger.info(
                f"Posted story to Facebook page {page_id}: {story_data.get('id', 'unknown')}"
            )
            return story_data

        except Exception as e:
            logger.error(f"Error posting story to Facebook: {e}")
            return {"success": False, "error": str(e)}

    def post_reel(
        self,
        page_id: str,
        video_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a reel to Facebook page."""
        try:
            endpoint = f"{self.BASE_URL}/{page_id}/reels"

            payload = {"description": caption or ""}

            # Upload video
            upload_endpoint = f"{self.BASE_URL}/{page_id}/videos"

            with httpx.Client(
                headers={"Authorization": f"Bearer {self.page_token}"},
                timeout=60.0,
            ) as upload_client:
                video_response = upload_client.post(
                    upload_endpoint,
                    files={"file": open(video_url, "rb")},
                    params={"description": caption or ""},
                )
                video_response.raise_for_status()
                video_data = video_response.json()
                video_fbid = video_data.get("id")

            if not video_fbid:
                return {"success": False, "error": "Failed to upload video"}

            # Create reel
            reel_response = self.client.post(
                endpoint,
                json={"source": video_fbid},
            )
            reel_response.raise_for_status()

            reel_data = reel_response.json()
            logger.info(
                f"Posted reel to Facebook page {page_id}: {reel_data.get('id', 'unknown')}"
            )
            return reel_data

        except Exception as e:
            logger.error(f"Error posting reel to Facebook: {e}")
            return {"success": False, "error": str(e)}

    def get_page_insights(
        self,
        page_id: str,
        metric: str = "page_impressions",
        period: str = "day",
    ) -> Optional[int]:
        """Get page insights."""
        try:
            endpoint = f"{self.BASE_URL}/{page_id}/insights"

            response = self.client.get(
                endpoint,
                params={
                    "metric": metric,
                    "period": period,
                },
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", [{}])[0].get("value")

        except Exception as e:
            logger.error(f"Error getting page insights: {e}")
            return None


def get_facebook_client(page_token: str) -> FacebookClient:
    """Get Facebook client instance."""
    return FacebookClient(page_token)

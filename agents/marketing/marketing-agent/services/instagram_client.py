from typing import Any, Dict, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.instagram_client")


class InstagramClient:
    """Client for Instagram Graph API."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def post_feed_image(
        self,
        media_id: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a feed image."""
        try:
            endpoint = f"{self.BASE_URL}/{media_id}"

            payload = {}
            if caption:
                payload["caption"] = caption

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Posted feed image: {data.get('id', 'unknown')}")
            return data

        except Exception as e:
            logger.error(f"Error posting feed image: {e}")
            return {"success": False, "error": str(e)}

    def post_reel(
        self,
        media_id: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a reel to Instagram."""
        try:
            endpoint = f"{self.BASE_URL}/{media_id}"

            payload = {}
            if caption:
                payload["caption"] = caption

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Posted reel: {data.get('id', 'unknown')}")
            return data

        except Exception as e:
            logger.error(f"Error posting reel: {e}")
            return {"success": False, "error": str(e)}

    def post_story(
        self,
        media_id: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a story to Instagram."""
        try:
            endpoint = f"{self.BASE_URL}/{media_id}"

            payload = {}
            if caption:
                payload["caption"] = caption

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Posted story: {data.get('id', 'unknown')}")
            return data

        except Exception as e:
            logger.error(f"Error posting story: {e}")
            return {"success": False, "error": str(e)}

    def get_media_insights(
        self,
        media_id: str,
        metric: str = "impressions",
    ) -> Optional[int]:
        """Get media insights."""
        try:
            endpoint = f"{self.BASE_URL}/{media_id}/insights"

            response = self.client.get(
                endpoint,
                params={
                    "metric": metric,
                    "period": "day",
                },
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", [{}])[0].get("value")

        except Exception as e:
            logger.error(f"Error getting media insights: {e}")
            return None


def get_instagram_client(access_token: str) -> InstagramClient:
    """Get Instagram client instance."""
    return InstagramClient(access_token)

from typing import Any, Dict, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.tiktok_client")


class TikTokClient:
    """Client for TikTok API."""

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def post_video(
        self,
        video_url: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Post a video to TikTok."""
        try:
            endpoint = f"{self.BASE_URL}/post/publish/video/url"

            payload: Dict[str, Any] = {}
            if description:
                payload["description"] = description
            if tags:
                payload["hashtag_names"] = tags

            response = self.client.post(
                endpoint, json=payload, params={"video_url": video_url}
            )
            response.raise_for_status()

            data = response.json()
            logger.info(
                f"Posted video to TikTok: {data.get('data', {}).get('video_id', 'unknown')}"
            )
            return data

        except Exception as e:
            logger.error(f"Error posting video to TikTok: {e}")
            return {"success": False, "error": str(e)}

    def get_video_stats(
        self,
        video_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get video statistics."""
        try:
            endpoint = f"{self.BASE_URL}/video/monitoring/{video_id}/get"

            response = self.client.get(endpoint)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved stats for video {video_id}")
            return data

        except Exception as e:
            logger.error(f"Error getting video stats: {e}")
            return None


def get_tiktok_client(access_token: str) -> TikTokClient:
    """Get TikTok client instance."""
    return TikTokClient(access_token)

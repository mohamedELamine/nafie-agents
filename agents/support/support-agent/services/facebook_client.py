import os
from typing import Any, Dict, List, Optional

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

    def get_comment(self, comment_id: str, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a comment by ID."""
        try:
            endpoint = f"{self.BASE_URL}/{comment_id}"

            response = self.client.get(
                endpoint,
                params={"fields": "id,from,message,created_time,comment_count"},
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data")

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting comment {comment_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting comment: {e}")
            return None

    def reply_comment(
        self, comment_id: str, message: str, page_id: str
    ) -> Dict[str, Any]:
        """Reply to a comment."""
        try:
            endpoint = f"{self.BASE_URL}/{comment_id}"

            response = self.client.post(
                endpoint,
                json={
                    "message": message,
                },
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Replied to comment {comment_id}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Error replying to comment {comment_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error replying: {e}")
            return {"success": False, "error": str(e)}

    def get_page_comments(
        self,
        page_id: str,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get page comments."""
        try:
            endpoint = f"{self.BASE_URL}/{page_id}/feed"

            params = {
                "fields": "id,from,message,created_time,comment_count,permalink_url",
                "limit": 100,
            }

            if since:
                params["since"] = since

            response = self.client.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            comments = data.get("data", [])

            logger.info(f"Retrieved {len(comments)} comments from page {page_id}")
            return comments

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting page comments: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting page comments: {e}")
            return []


def get_facebook_client(page_token: Optional[str] = None) -> FacebookClient:
    """Get Facebook client instance."""
    return FacebookClient(page_token or os.environ.get("META_ACCESS_TOKEN", ""))

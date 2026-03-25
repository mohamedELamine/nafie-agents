from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.helpscout_client")


class HelpScoutClient:
    """Client for HelpScout API."""

    BASE_URL = "https://api.helpscout.net/v2"
    CONVERSATIONS_ENDPOINT = "/conversations"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def get_conversations(
        self, since: Optional[datetime] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversations from HelpScout."""
        try:
            params: Dict[str, Any] = {}

            if since:
                params["filter[modifiedAtAfter]"] = since.isoformat()

            if status:
                params["filter[status]"] = status

            response = self.client.get(
                f"{self.BASE_URL}{self.CONVERSATIONS_ENDPOINT}", params=params
            )
            response.raise_for_status()

            data = response.json()
            return data.get("conversations", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting conversations: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching conversations: {e}")
            return []

    def get_conversation_stats(
        self, since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get conversation statistics."""
        try:
            stats = {
                "total": 0,
                "open": 0,
                "closed": 0,
                "resolved": 0,
            }

            conversations = self.get_conversations(since=since)

            for conv in conversations:
                stats["total"] += 1
                status = conv.get("status", "open")
                if status == "open":
                    stats["open"] += 1
                elif status == "closed":
                    stats["closed"] += 1
                elif status == "resolved":
                    stats["resolved"] += 1

            return stats

        except Exception as e:
            logger.error(f"Error getting conversation stats: {e}")
            return {
                "total": 0,
                "open": 0,
                "closed": 0,
                "resolved": 0,
            }


def get_conversations(
    api_key: str, since: Optional[datetime] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get conversations from HelpScout."""
    client = HelpScoutClient(api_key)
    return client.get_conversations(since, status)

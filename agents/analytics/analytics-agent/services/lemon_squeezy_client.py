from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.lemon_squeezy_client")


class LemonSqueezyClient:
    """Client for Lemon Squeezy API."""

    BASE_URL = "https://api.lemonsqueezy.com/v1"
    API_VERSION = "2024-01-25"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/vnd.api+json",
            },
            timeout=30.0,
        )

    def get_orders(
        self,
        since: Optional[datetime] = None,
        use_occurred_at: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get orders from Lemon Squeezy."""
        try:
            params: Dict[str, Any] = {"include": "first_order_item"}

            if since:
                if use_occurred_at:
                    params["filter[occurred_at_after]"] = since.isoformat()
                else:
                    params["filter[created_at_after]"] = since.isoformat()

            response = self.client.get(f"{self.BASE_URL}/orders", params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting orders from LS: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching orders: {e}")
            return []

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a single order by ID."""
        try:
            response = self.client.get(f"{self.BASE_URL}/orders/{order_id}")
            response.raise_for_status()

            data = response.json()
            return data.get("data")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching order: {e}")
            return None

    def get_licenses(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get licenses from Lemon Squeezy."""
        try:
            params: Dict[str, Any] = {}

            if since:
                params["filter[created_at_after]"] = since.isoformat()

            response = self.client.get(f"{self.BASE_URL}/licenses", params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting licenses from LS: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching licenses: {e}")
            return []

    def get_store_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        try:
            response = self.client.get(f"{self.BASE_URL}/store/stats")
            response.raise_for_status()

            data = response.json()
            return data.get("data", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting store stats: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching store stats: {e}")
            return {}


def get_orders(
    api_key: str,
    since: Optional[datetime] = None,
    use_occurred_at: bool = True,
) -> List[Dict[str, Any]]:
    """Get orders from Lemon Squeezy."""
    client = LemonSqueezyClient(api_key)
    return client.get_orders(since, use_occurred_at)

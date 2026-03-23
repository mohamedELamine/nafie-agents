from typing import Any, Dict, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.whatsapp_client")


class WhatsAppClient:
    """Client for WhatsApp Business API."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def send_broadcast_template(
        self,
        recipient: str,
        template_name: str,
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """Send a broadcast template."""
        try:
            endpoint = f"{self.BASE_URL}/{self.phone_number_id}/messages"

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                },
            }

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Sent broadcast template to {recipient}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Error sending broadcast template: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending broadcast template: {e}")
            return {"success": False, "error": str(e)}

    def get_template_status(
        self,
        template_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Get status of a template."""
        try:
            endpoint = f"{self.BASE_URL}/{self.phone_number_id}/message_templates"

            response = self.client.get(
                endpoint,
                params={
                    "name": template_name,
                },
            )
            response.raise_for_status()

            data = response.json()
            return data

        except Exception as e:
            logger.error(f"Error getting template status: {e}")
            return None


def get_whatsapp_client(
    access_token: str,
    phone_number_id: str,
) -> WhatsAppClient:
    """Get WhatsApp client instance."""
    return WhatsAppClient(access_token, phone_number_id)

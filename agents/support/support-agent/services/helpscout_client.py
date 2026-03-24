import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from ..logging_config import get_logger

logger = get_logger("services.helpscout_client")


class HelpScoutClient:
    """Client for HelpScout API."""

    BASE_URL = "https://api.helpscout.net/v2"
    CONVERSATIONS_ENDPOINT = "/conversations"
    CUSTOMERS_ENDPOINT = "/customers"
    MAILBOXES_ENDPOINT = "/mailboxes"

    def __init__(self, api_key: str, mailbox_id: int):
        self.api_key = api_key
        self.mailbox_id = mailbox_id
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID."""
        try:
            endpoint = f"{self.CONVERSATIONS_ENDPOINT}/{conversation_id}"

            response = self.client.get(endpoint)
            response.raise_for_status()

            data = response.json()
            return data.get("conversation")

        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None

    def reply(
        self,
        conversation_id: Optional[str] = None,
        body: str = "",
        is_html: bool = False,
        ticket_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reply to a conversation."""
        try:
            conversation_id = conversation_id or ticket_id
            if not conversation_id:
                raise ValueError("conversation_id is required")

            endpoint = f"{self.CONVERSATIONS_ENDPOINT}/{conversation_id}/reply"

            content = body if is_html else body

            response = self.client.post(
                endpoint,
                json={
                    "body": content,
                    "textFormat": "text" if not is_html else "html",
                },
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Replied to conversation {conversation_id}")
            return data.get("reply")

        except httpx.HTTPStatusError as e:
            logger.error(f"Error replying to conversation {conversation_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error replying: {e}")
            return {"success": False, "error": str(e)}

    def close_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Close a conversation."""
        try:
            endpoint = f"{self.CONVERSATIONS_ENDPOINT}/{conversation_id}"

            response = self.client.put(
                endpoint,
                json={
                    "status": "closed",
                },
            )
            response.raise_for_status()

            logger.info(f"Closed conversation {conversation_id}")
            return {"success": True}

        except httpx.HTTPStatusError as e:
            logger.error(f"Error closing conversation {conversation_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error closing conversation: {e}")
            return {"success": False, "error": str(e)}

    def assign_conversation(
        self,
        conversation_id: str,
        assignee_id: str,
    ) -> Dict[str, Any]:
        """Assign a conversation to a specific assignee."""
        try:
            endpoint = f"{self.CONVERSATIONS_ENDPOINT}/{conversation_id}"

            response = self.client.put(
                endpoint,
                json={
                    "assignee": {
                        "id": assignee_id,
                    },
                },
            )
            response.raise_for_status()

            logger.info(f"Assigned conversation {conversation_id} to {assignee_id}")
            return {"success": True}

        except httpx.HTTPStatusError as e:
            logger.error(f"Error assigning conversation {conversation_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error assigning conversation: {e}")
            return {"success": False, "error": str(e)}

    def add_note(
        self,
        conversation_id: Optional[str] = None,
        body: Optional[str] = None,
        ticket_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a note to a conversation."""
        try:
            conversation_id = conversation_id or ticket_id
            body = body or note
            if not conversation_id:
                raise ValueError("conversation_id is required")
            if body is None:
                raise ValueError("body is required")

            endpoint = f"{self.CONVERSATIONS_ENDPOINT}/{conversation_id}/note"

            response = self.client.post(
                endpoint,
                json={
                    "body": body,
                    "textFormat": "text",
                },
            )
            response.raise_for_status()

            logger.info(f"Added note to conversation {conversation_id}")
            return {"success": True}

        except httpx.HTTPStatusError as e:
            logger.error(f"Error adding note to conversation {conversation_id}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return {"success": False, "error": str(e)}


def get_helpscout_client(
    api_key: Optional[str] = None,
    mailbox_id: Optional[int] = None,
) -> HelpScoutClient:
    """Get HelpScout client instance."""
    resolved_mailbox_id = mailbox_id
    if resolved_mailbox_id is None:
        resolved_mailbox_id = int(
            os.environ.get("HELPSCOUT_MAILBOX_ID")
            or os.environ.get("HELP_SCOUT_MAILBOX_ID", "0")
        )
    return HelpScoutClient(
        api_key
        or os.environ.get("HELPSCOUT_API_KEY")
        or os.environ.get("HELP_SCOUT_API_KEY", ""),
        resolved_mailbox_id,
    )

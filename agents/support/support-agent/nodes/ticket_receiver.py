from datetime import datetime, timezone
from typing import Any, Dict

from ..logging_config import get_logger
from ..models import Platform, RiskLevel

logger = get_logger("nodes.ticket_receiver")


def make_ticket_receiver_node() -> callable:
    """Create the ticket receiver node."""

    def ticket_receiver_node(ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Receive and convert webhook payload to a SupportTicket dict."""
        try:
            platform_str = ticket_data.get("platform", "helpscout").lower()

            # Map platform string to Platform enum (values are lowercase)
            try:
                platform = Platform(platform_str)
            except ValueError:
                logger.warning(f"Unknown platform: {platform_str}, defaulting to helpscout")
                platform = Platform.HELPSCOUT

            # Generate a fallback ticket_id if missing
            fallback_id = f"ticket_{int(datetime.now(timezone.utc).timestamp())}"
            ticket_id = (
                ticket_data.get("ticket_id")
                or ticket_data.get("conversation_id")
                or ticket_data.get("id")
                or fallback_id
            )

            # Parse occurred_at — fallback to utcnow with warning
            raw_created = ticket_data.get("created_at")
            if raw_created:
                try:
                    created_at = datetime.fromisoformat(raw_created)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid created_at '{raw_created}', using current UTC time"
                    )
                    created_at = datetime.now(timezone.utc)
            else:
                created_at = datetime.now(timezone.utc)

            ticket = {
                "ticket_id":       ticket_id,
                "platform":        platform,
                "conversation_id": ticket_data.get("conversation_id"),
                "page_id":         ticket_data.get("page_id"),
                "customer_email":  (
                    ticket_data.get("customer_email")
                    or ticket_data.get("customer", {}).get("email")
                ),
                "order_id":        ticket_data.get("order_id"),
                "license_key":     ticket_data.get("license_key"),
                "customer_name":   ticket_data.get("customer", {}).get("name"),
                "message":         ticket_data.get("message") or ticket_data.get("body", ""),
                "subject":         ticket_data.get("subject"),
                "is_html":         ticket_data.get("is_html", False),
                "created_at":      created_at,
                "priority":        ticket_data.get("priority", RiskLevel.LOW.value),
            }

            logger.info(f"Received ticket {ticket_id} from {platform.value}")

            return {
                "success":  True,
                "ticket":   ticket,
                "platform": platform.value,
            }

        except Exception as e:
            logger.error(f"Error in ticket_receiver_node: {e}")
            return {"success": False, "error": str(e)}

    return ticket_receiver_node

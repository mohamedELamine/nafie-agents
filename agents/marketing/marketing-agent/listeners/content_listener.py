from datetime import datetime
from typing import Any, Dict

from ..db import campaign_log
from ..services import get_redis_bus
from ..state import MarketingState, make_initial_state
from ..logging_config import get_logger

logger = get_logger("listeners.content_listener")


def make_content_listener(redis) -> callable:
    """Create the content listener."""

    def content_listener() -> None:
        """Listen for CONTENT_READY events."""
        try:
            redis_bus = get_redis_bus(redis_url="redis://localhost:6379/0")

            # Check if we have a campaign waiting for content
            # For now, just log the event
            messages = redis_bus.read_group(
                stream="marketing:events",
                consumer_name="content_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                event_type = message.get("event_type")

                if event_type == "CONTENT_READY":
                    campaign_id = message.get("campaign_id")
                    logger.info(f"CONTENT_READY received for campaign {campaign_id}")

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.utcnow().timestamp())}",
                        "campaign_id": campaign_id,
                        "event_type": "CONTENT_RECEIVED",
                        "details": message,
                    }

                    conn = __import__("psycopg2").connect(
                        "postgresql://marketing:password@localhost:5432/marketing_db"
                    )
                    campaign_log.save_log(conn, log_entry)
                    conn.close()

                redis_bus.ack("marketing:events", message_id)

        except Exception as e:
            logger.error(f"Error in content listener: {e}")

    return content_listener

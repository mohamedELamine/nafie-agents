from datetime import datetime
from typing import Any, Dict

from ..db import campaign_log
from ..services import get_redis_bus
from ..logging_config import get_logger

logger = get_logger("listeners.assets_listener")


def make_assets_listener(redis) -> callable:
    """Create the assets listener."""

    def assets_listener() -> None:
        """Listen for THEME_ASSETS_READY events."""
        try:
            redis_bus = get_redis_bus(redis_url="redis://localhost:6379/0")

            messages = redis_bus.read_group(
                stream="marketing:events",
                consumer_name="assets_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                event_type = message.get("event_type")

                if event_type == "THEME_ASSETS_READY":
                    campaign_id = message.get("campaign_id")
                    logger.info(
                        f"THEME_ASSETS_READY received for campaign {campaign_id}"
                    )

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.utcnow().timestamp())}",
                        "campaign_id": campaign_id,
                        "event_type": "ASSETS_RECEIVED",
                        "details": message,
                    }

                    conn = __import__("psycopg2").connect(
                        "postgresql://marketing:password@localhost:5432/marketing_db"
                    )
                    campaign_log.save_log(conn, log_entry)
                    conn.close()

                redis_bus.ack("marketing:events", message_id)

        except Exception as e:
            logger.error(f"Error in assets listener: {e}")

    return assets_listener

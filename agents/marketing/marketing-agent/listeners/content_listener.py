import os
from datetime import datetime
from typing import Any, Dict

import psycopg2
from core.contracts import EVENT_CONTENT_READY, STREAM_CONTENT_EVENTS
from ..db import campaign_log
from ..services import get_redis_bus
from ..logging_config import get_logger

logger = get_logger("listeners.content_listener")


def make_content_listener(redis) -> callable:
    """Create the content listener."""

    def _connect():
        dsn = (
            os.environ.get("MARKETING_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
            or "postgresql://marketing:password@localhost:5432/marketing_db"
        )
        return psycopg2.connect(dsn)

    def content_listener() -> None:
        """Listen for CONTENT_READY events."""
        try:
            redis_bus = get_redis_bus(redis_url="redis://localhost:6379/0")

            # Check if we have a campaign waiting for content
            # For now, just log the event
            messages = redis_bus.read_group(
                stream=STREAM_CONTENT_EVENTS,
                consumer_name="content_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                event_type = message.get("event_type")

                if event_type == EVENT_CONTENT_READY:
                    data = message.get("data", {})
                    campaign_id = data.get("campaign_id")
                    logger.info(
                        "CONTENT_READY received for theme=%s campaign=%s",
                        data.get("theme_slug"),
                        campaign_id,
                    )

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.utcnow().timestamp())}",
                        "campaign_id": campaign_id,
                        "event_type": "CONTENT_RECEIVED",
                        "details": message,
                    }

                    conn = _connect()
                    campaign_log.save_log(conn, log_entry)
                    conn.close()

                if message_id:
                    redis_bus.ack(STREAM_CONTENT_EVENTS, message_id)

        except Exception as e:
            logger.error(f"Error in content listener: {e}")

    return content_listener

import os
from datetime import datetime, timezone

from core.contracts import STREAM_ANALYTICS_SIGNALS
from ..db import campaign_log
from ..db.connection import get_conn
from ..services import get_redis_bus
from ..logging_config import get_logger

logger = get_logger("listeners.analytics_listener")


def make_analytics_listener(redis) -> callable:
    """Create the analytics listener."""

    def analytics_listener() -> None:
        """Listen for ANALYTICS_SIGNAL events."""
        try:
            redis_bus = get_redis_bus(redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

            messages = redis_bus.read_group(
                stream=STREAM_ANALYTICS_SIGNALS,
                consumer_name="analytics_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                signal_type = message.get("signal_type")
                data = message.get("data", {})

                if signal_type in ["best_time", "best_channel"]:
                    logger.info(
                        f"ANALYTICS_SIGNAL (AUTO_APPLICABLE) received: {signal_type} "
                        f"for theme {message.get('theme_slug', 'unknown')}"
                    )

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.now(timezone.utc).timestamp())}",
                        "campaign_id": message.get("campaign_id"),
                        "event_type": "ANALYTICS_SIGNAL_RECEIVED",
                        "details": {
                            "signal_type": signal_type,
                            "data": data,
                        },
                    }

                    with get_conn() as conn:
                        campaign_log.save_log(conn, log_entry)

                redis_bus.ack(STREAM_ANALYTICS_SIGNALS, message_id)

        except Exception as e:
            logger.error(f"Error in analytics listener: {e}")

    return analytics_listener

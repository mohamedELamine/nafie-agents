from datetime import datetime
from typing import Any, Dict

from ..db import campaign_log
from ..services import get_redis_bus
from ..logging_config import get_logger

logger = get_logger("listeners.analytics_listener")


def make_analytics_listener(redis) -> callable:
    """Create the analytics listener."""

    def analytics_listener() -> None:
        """Listen for ANALYTICS_SIGNAL events."""
        try:
            redis_bus = get_redis_bus(redis_url="redis://localhost:6379/0")

            messages = redis_bus.read_group(
                stream="analytics:signals",
                consumer_name="analytics_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                signal_type = message.get("signal_type")
                data = message.get("data", {})

                if signal_type in ["best_post_time", "best_format", "engagement_peak"]:
                    logger.info(
                        f"ANALYTICS_SIGNAL (AUTO_APPLICABLE) received: {signal_type} "
                        f"for campaign {message.get('campaign_id', 'unknown')}"
                    )

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.utcnow().timestamp())}",
                        "campaign_id": message.get("campaign_id"),
                        "event_type": "ANALYTICS_SIGNAL_RECEIVED",
                        "details": {
                            "signal_type": signal_type,
                            "data": data,
                        },
                    }

                    conn = __import__("psycopg2").connect(
                        "postgresql://marketing:password@localhost:5432/marketing_db"
                    )
                    campaign_log.save_log(conn, log_entry)
                    conn.close()

                redis_bus.ack("analytics:signals", message_id)

        except Exception as e:
            logger.error(f"Error in analytics listener: {e}")

    return analytics_listener

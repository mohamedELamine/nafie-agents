from datetime import datetime, timezone

from core.contracts import EVENT_THEME_ASSETS_READY, STREAM_ASSET_EVENTS
from ..db import campaign_log
from ..db.connection import get_conn
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
                stream=STREAM_ASSET_EVENTS,
                consumer_name="assets_listener",
                count=10,
                block_ms=1000,
                min_id=">",
            )

            for message in messages:
                message_id = message.pop("__message_id", None)
                event_type = message.get("event_type")

                if event_type == EVENT_THEME_ASSETS_READY:
                    data = message.get("data", {})
                    campaign_id = data.get("campaign_id")
                    logger.info(
                        "THEME_ASSETS_READY received for theme=%s campaign=%s",
                        data.get("theme_slug"),
                        campaign_id,
                    )

                    # Log the event
                    log_entry = {
                        "log_id": f"log_{int(datetime.now(timezone.utc).timestamp())}",
                        "campaign_id": campaign_id,
                        "event_type": "ASSETS_RECEIVED",
                        "details": message,
                    }

                    with get_conn() as conn:
                        campaign_log.save_log(conn, log_entry)

                if message_id:
                    redis_bus.ack(STREAM_ASSET_EVENTS, message_id)

        except Exception as e:
            logger.error(f"Error in assets listener: {e}")

    return assets_listener

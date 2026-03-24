import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import RedisError

from ..logging_config import get_logger

logger = get_logger("services.redis_bus")


class RedisBus:
    """Redis-based message bus for analytics events."""

    EVENT_STREAM = "product-events"
    SUPPORT_STREAM = "support-events"
    MARKETING_STREAM = "marketing-events"
    CONTENT_STREAM = "content-events"
    BUILDER_STREAM = "builder-events"

    ANALYTICS_SIGNAL_CHANNEL = "analytics:signals"
    WEEKLY_REPORT_CHANNEL = "analytics:reports:weekly"
    MONTHLY_REPORT_CHANNEL = "analytics:reports:monthly"
    OWNER_ALERT_CHANNEL = "analytics:alerts:owner"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = redis.from_url(redis_url, decode_responses=True)
        self._ensure_consumer_group()

    def _ensure_consumer_group(self) -> None:
        """Ensure the consumer group exists."""
        try:
            # Create stream if not exists
            if not self.client.exists(self.EVENT_STREAM):
                self.client.xadd(self.EVENT_STREAM, {"init": "true"})

            # Create consumer group if not exists
            try:
                self.client.xgroup_create(
                    self.EVENT_STREAM, "analytics-agent", id="0", mkstream=True
                )
            except redis.exceptions.ResponseError:
                # Group already exists, that's fine
                pass

        except RedisError as e:
            logger.error(f"Error ensuring consumer group: {e}")

    def publish(self, channel: str, message: Dict[str, Any]) -> Optional[str]:
        """Publish a message to a Redis channel."""
        try:
            message_json = json.dumps(message, default=str)
            result = self.client.publish(channel, message_json)

            if result:
                logger.debug(f"Published to {channel}: {message.get('type')}")
                return message_json
            return None
        except RedisError as e:
            logger.error(f"Error publishing to {channel}: {e}")
            return None

    def publish_stream(self, stream: str, message: Dict[str, Any]) -> Optional[str]:
        """Publish a message to a stream using the shared data field wrapper."""
        try:
            self.ensure_consumer_group(stream, "analytics-agent")
            payload = json.dumps(message, default=str)
            message_id = self.client.xadd(stream, {"data": payload})
            logger.debug(f"Published to stream {stream}: {message.get('event_type')}")
            return message_id
        except RedisError as e:
            logger.error(f"Error publishing to stream {stream}: {e}")
            return None

    def read_group(
        self,
        stream: str,
        consumer_group: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 1000,
        min_id: str = ">",
    ) -> List[Dict[str, Any]]:
        """Read messages from a stream using consumer group."""
        try:
            self.ensure_consumer_group(stream, consumer_group)
            messages = self.client.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream: min_id},
                count=count,
                block=block_ms,
            )

            events = []
            for stream_name, stream_messages in messages:
                for message_id, data in stream_messages:
                    if "data" in data:
                        try:
                            parsed = json.loads(data["data"])
                        except (TypeError, json.JSONDecodeError):
                            parsed = dict(data)
                    else:
                        parsed = dict(data)
                    parsed["__message_id"] = message_id
                    events.append(parsed)

            return events

        except RedisError as e:
            logger.error(f"Error reading from stream {stream}: {e}")
            return []

    def ensure_consumer_group(self, stream: str, consumer_group: str) -> None:
        """Ensure a consumer group exists for the requested stream."""
        try:
            if not self.client.exists(stream):
                self.client.xadd(stream, {"init": "true"})
            try:
                self.client.xgroup_create(stream, consumer_group, id="0", mkstream=True)
            except redis.exceptions.ResponseError:
                pass
        except RedisError as e:
            logger.error(f"Error ensuring consumer group for {stream}: {e}")

    def ack(self, stream: str, message_id: str) -> None:
        """Acknowledge a message from a stream."""
        try:
            self.client.xack(stream, "analytics-agent", message_id)
            logger.debug(f"Acked message {message_id} from {stream}")
        except RedisError as e:
            logger.error(f"Error acking message {message_id}: {e}")

    def build_analytics_event(
        self,
        event_type: str,
        source_agent: str,
        theme_slug: str,
        raw_data: Dict[str, Any],
        occurred_at: datetime,
    ) -> Dict[str, Any]:
        """Build a structured analytics event."""
        return {
            "event_id": f"{event_type}_{int(occurred_at.timestamp())}_{len(theme_slug)}",
            "event_type": event_type,
            "source_agent": source_agent,
            "theme_slug": theme_slug,
            "raw_data": raw_data,
            "occurred_at": occurred_at.isoformat(),
            "received_at": datetime.utcnow().isoformat(),
        }


def get_redis_bus(redis_url: str) -> RedisBus:
    """Get RedisBus instance."""
    return RedisBus(redis_url)

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import RedisError

from core.contracts import STREAM_SUPPORT_EVENTS, build_ecosystem_event
from ..logging_config import get_logger

logger = get_logger("services.redis_bus")


class RedisBus:
    """Redis-based message bus for support events."""

    EVENTS_STREAM = STREAM_SUPPORT_EVENTS
    RECURRING_ISSUES_STREAM = "support:recurring_issues"

    CONSUMER_GROUP = "support-agent"
    CONSUMER_NAME = "support-consumer"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = redis.from_url(redis_url, decode_responses=True)
        self._ensure_consumer_group()

    def _ensure_consumer_group(self, stream: Optional[str] = None) -> None:
        """Ensure the consumer group exists."""
        try:
            stream_name = stream or self.EVENTS_STREAM
            # Create stream if not exists
            if not self.client.exists(stream_name):
                self.client.xadd(stream_name, {"init": "true"})

            # Create consumer group if not exists
            try:
                self.client.xgroup_create(
                    stream_name,
                    self.CONSUMER_GROUP,
                    id="0",
                    mkstream=True,
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

    def build_event(
        self,
        event_type: str,
        ticket_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a support event."""
        return build_ecosystem_event(
            event_type=event_type,
            data={"ticket_id": ticket_id, **data},
            source="support_agent",
        )

    def publish_stream(self, stream: str, message: Dict[str, Any]) -> Optional[str]:
        """Publish a message to a Redis stream using the shared envelope format."""
        try:
            self._ensure_consumer_group(stream)
            payload = json.dumps(message, default=str)
            message_id = self.client.xadd(stream, {"data": payload})
            logger.debug(f"Published stream event to {stream}: {message.get('event_type')}")
            return message_id
        except RedisError as e:
            logger.error(f"Error publishing to stream {stream}: {e}")
            return None

    def publish_message(self, channel: str, message: Dict[str, Any]) -> Optional[str]:
        """Backward-compatible alias used by older nodes."""
        return self.publish(channel, message)

    def read_group(
        self,
        stream: str,
        consumer_name: Optional[str] = None,
        count: int = 10,
        block_ms: int = 1000,
        min_id: str = ">",
    ) -> List[Dict[str, Any]]:
        """Read messages from a stream using consumer group."""
        try:
            consumer = consumer_name or self.CONSUMER_NAME
            self._ensure_consumer_group(stream)

            messages = self.client.xreadgroup(
                groupname=self.CONSUMER_GROUP,
                consumername=consumer,
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

    def ack(self, stream: str, message_id: str) -> None:
        """Acknowledge a message from a stream."""
        try:
            self.client.xack(stream, self.CONSUMER_GROUP, message_id)
            logger.debug(f"Acked message {message_id} from {stream}")
        except RedisError as e:
            logger.error(f"Error acking message {message_id}: {e}")


def get_redis_bus(redis_url: Optional[str] = None) -> RedisBus:
    """Get RedisBus instance."""
    return RedisBus(redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379"))

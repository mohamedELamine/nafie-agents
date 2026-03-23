import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import RedisError

from ..logging_config import get_logger

logger = get_logger("services.redis_bus")


class RedisBus:
    """Redis-based message bus for marketing events."""

    CHECKPOINT_CHANNEL = "marketing:checkpoints"
    EVENTS_CHANNEL = "marketing:events"

    CONSUMER_GROUP = "marketing-agent"
    CONSUMER_NAME = "marketing-consumer"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = redis.from_url(redis_url, decode_responses=True)
        self._ensure_consumer_group()

    def _ensure_consumer_group(self) -> None:
        """Ensure the consumer group exists."""
        try:
            # Create stream if not exists
            if not self.client.exists(self.EVENTS_CHANNEL):
                self.client.xadd(self.EVENTS_CHANNEL, {"init": "true"})

            # Create consumer group if not exists
            try:
                self.client.xgroup_create(
                    self.EVENTS_CHANNEL,
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
        campaign_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a marketing event."""
        return {
            "event_id": f"{event_type}_{int(datetime.utcnow().timestamp())}_{len(campaign_id)}",
            "event_type": event_type,
            "campaign_id": campaign_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def create_checkpoint(
        self, campaign_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        """Create a checkpoint for a campaign."""
        try:
            checkpoint_id = (
                f"checkpoint_{campaign_id}_{int(datetime.utcnow().timestamp())}"
            )

            self.client.setex(
                f"checkpoint:{checkpoint_id}",
                259200,  # 72 hours TTL
                json.dumps(checkpoint_data, default=str),
            )

            self.publish(
                self.CHECKPOINT_CHANNEL,
                {
                    "checkpoint_id": checkpoint_id,
                    "campaign_id": campaign_id,
                    "data": checkpoint_data,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

            logger.debug(
                f"Created checkpoint {checkpoint_id} for campaign {campaign_id}"
            )
            return checkpoint_id

        except Exception as e:
            logger.error(f"Error creating checkpoint: {e}")
            return ""

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
                    # Store message ID for ack
                    data["__message_id"] = message_id
                    events.append(data)

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


def get_redis_bus(redis_url: str) -> RedisBus:
    """Get RedisBus instance."""
    return RedisBus(redis_url)

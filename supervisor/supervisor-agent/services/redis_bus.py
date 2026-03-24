import logging
from dataclasses import asdict
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone
import uuid

from models import EventEnvelope

logger = logging.getLogger("supervisor.redis_bus")


class RedisBus:
    def __init__(
        self, host: str = "localhost", port: int = 6379, password: Optional[str] = None, db: int = 0
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self._redis = None

    async def _connect(self):
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis

            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    async def publish_supervisor_event(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> bool:
        """Publish supervisor event with EventEnvelope"""
        try:
            await self._connect()

            envelope = EventEnvelope(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                data=data,
                correlation_id=correlation_id or str(uuid.uuid4()),
                causation_id=causation_id or str(uuid.uuid4()),
                workflow_id=workflow_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            message = json.dumps(asdict(envelope))
            stream = f"streams:{channel}"
            await self._redis.xadd(stream, {"payload": message})
            await self._redis.publish(channel, message)

            logger.info(f"Published {event_type} to {channel}")
            return True

        except Exception as e:
            logger.error(f"Error publishing supervisor event: {e}")
            raise

    async def read_group(
        self, channel: str, group: str, consumer: str, count: int = 1
    ) -> Optional[dict]:
        """Read message from Redis stream group"""
        try:
            await self._connect()

            stream = f"streams:{channel}"
            result = await self._redis.xreadgroup(
                group, consumer, {stream: ">"}, count=count, block=0
            )

            if result:
                message = result[0][1][0]
                message_id = message[0]
                payload = message[1].get("payload", "{}")
                message_data = json.loads(payload)

                return {"id": message_id, "data": message_data}

            return None

        except Exception as e:
            logger.error(f"Error reading from group: {e}")
            raise

    async def ack(self, channel: str, group: str, message_id: str) -> bool:
        """Acknowledge message"""
        try:
            await self._connect()

            stream = f"streams:{channel}"
            await self._redis.xack(stream, group, message_id)

            return True

        except Exception as e:
            logger.error(f"Error acknowledging message: {e}")
            raise

    async def ensure_consumer_group(
        self, channel: str, group: str, consumer: str = "default"
    ) -> bool:
        """Ensure consumer group exists"""
        try:
            await self._connect()

            await self._redis.xgroup_create(f"streams:{channel}", group, id="0", mkstream=True)

            logger.info(f"Consumer group {group} created for {channel}")
            return True

        except Exception as e:
            if "BUSYGROUP" in str(e):
                return True
            logger.error(f"Error creating consumer group: {e}")
            raise

    def build_supervisor_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> EventEnvelope:
        """Build supervisor event envelope"""
        return EventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            data=data,
            correlation_id=correlation_id or str(uuid.uuid4()),
            causation_id=causation_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


redis_bus = RedisBus()

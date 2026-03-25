import logging
import json
from typing import Optional, Dict, Any

from core.contracts import build_ecosystem_event

logger = logging.getLogger("visual_production.redis_bus")


class RedisBus:
    def __init__(self, host: str, port: int, password: Optional[str] = None, db: int = 0):
        self.host = host
        self.port = port
        self.password = password
        self.db = db

    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a channel"""
        try:
            await self._connect()
            data = json.dumps(message)
            await self._redis.publish(channel, data)
            logger.info(f"Published to {channel}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")
            raise

    async def publish_stream(self, stream_name: str, data: Dict[str, Any]) -> bool:
        """Add data to a Redis stream"""
        try:
            await self._connect()
            await self._redis.xadd(
                stream_name,
                {"data": json.dumps(data, default=str)},
            )
            logger.info(f"Added to stream {stream_name}: {data}")
            return True
        except Exception as e:
            logger.error(f"Error adding to stream {stream_name}: {e}")
            raise

    async def build_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "visual_production_agent",
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build an event with standard structure"""
        return build_ecosystem_event(
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
        )

    async def checkpoint_save(self, key: str, data: Dict[str, Any], ttl: int = 48 * 3600):
        """Save checkpoint with TTL"""
        try:
            await self._connect()
            await self._redis.setex(f"checkpoint:{key}", ttl, json.dumps(data))
            logger.info(f"Saved checkpoint {key}")
        except Exception as e:
            logger.error(f"Error saving checkpoint {key}: {e}")
            raise

    async def checkpoint_get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint data"""
        try:
            await self._connect()
            data = await self._redis.get(f"checkpoint:{key}")

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Error getting checkpoint {key}: {e}")
            raise

    async def checkpoint_delete(self, key: str) -> bool:
        """Delete checkpoint"""
        try:
            await self._connect()
            result = await self._redis.delete(f"checkpoint:{key}")

            return result > 0

        except Exception as e:
            logger.error(f"Error deleting checkpoint {key}: {e}")
            raise

    async def _connect(self):
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis

            if not hasattr(self, "_redis"):
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    decode_responses=False,
                )
                logger.info("Redis connected")
        except ImportError:
            raise ImportError(
                "redis package not installed. Install with: pip install redis[hiredis]"
            )
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise

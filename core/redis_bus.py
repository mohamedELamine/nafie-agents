"""
core/redis_bus.py
=================
حافلة الأحداث المشتركة بين جميع الوكلاء.
تعتمد على Redis Pub/Sub + Redis Streams للموثوقية.
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any

import redis.asyncio as aioredis

from core.state import BusinessEvent, EventType, AgentName

logger = logging.getLogger(__name__)


class RedisBus:
    """
    حافلة الأحداث المركزية.

    القناة الرئيسية: `ar_themes:events`
    قناة كل وكيل:   `ar_themes:agent:<agent_name>`
    Stream الموثوق:  `ar_themes:stream` (للأحداث الحرجة)
    """

    MAIN_CHANNEL   = "ar_themes:events"
    AGENT_CHANNEL  = "ar_themes:agent:{agent}"
    MAIN_STREAM    = "ar_themes:stream"
    HEARTBEAT_KEY  = "ar_themes:heartbeat:{agent}"

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._pub: Optional[aioredis.Redis] = None
        self._sub: Optional[aioredis.Redis] = None
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._agent_name: Optional[AgentName] = None

    async def connect(self, agent_name: AgentName) -> None:
        self._agent_name = agent_name
        self._pub = await aioredis.from_url(self.redis_url, decode_responses=True)
        self._sub = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"[{agent_name}] ✓ متصل بـ Redis Bus")

    async def disconnect(self) -> None:
        if self._pub:
            await self._pub.aclose()
        if self._sub:
            await self._sub.aclose()

    # ── النشر ────────────────────────────────────────────

    async def publish(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        target: Optional[AgentName] = None,
        priority: int = 5,
        trace_id: Optional[str] = None,
    ) -> str:
        """نشر حدث على الحافلة. يعيد event_id."""

        event: BusinessEvent = {
            "event_id":   str(uuid.uuid4()),
            "event_type": event_type,
            "source":     self._agent_name,
            "target":     target,
            "payload":    payload,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "trace_id":   trace_id or str(uuid.uuid4()),
            "priority":   priority,
        }

        message = json.dumps(event, ensure_ascii=False)

        # ١. النشر على القناة العامة
        await self._pub.publish(self.MAIN_CHANNEL, message)

        # ٢. إن كان الحدث موجَّهاً لوكيل بعينه — القناة الخاصة
        if target:
            channel = self.AGENT_CHANNEL.format(agent=target)
            await self._pub.publish(channel, message)

        # ٣. للأحداث ذات الأولوية العالية (≤ 2) — Redis Stream للموثوقية
        if priority <= 2:
            await self._pub.xadd(
                self.MAIN_STREAM,
                {"data": message},
                maxlen=10_000,
            )

        logger.debug(f"[{self._agent_name}] → {event_type} | target={target} | id={event['event_id'][:8]}")
        return event["event_id"]

    # ── الاشتراك ─────────────────────────────────────────

    def on(self, event_type: EventType, handler: Callable) -> None:
        """تسجيل معالج لنوع حدث."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def listen(self) -> None:
        """الاستماع للأحداث الواردة — يعمل إلى الأبد."""
        pubsub = self._sub.pubsub()

        # الاشتراك في القناة العامة والقناة الخاصة بهذا الوكيل
        channels = [
            self.MAIN_CHANNEL,
            self.AGENT_CHANNEL.format(agent=self._agent_name),
        ]
        await pubsub.subscribe(*channels)
        logger.info(f"[{self._agent_name}] يستمع على: {channels}")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event: BusinessEvent = json.loads(message["data"])
                await self._dispatch(event)
            except Exception as e:
                logger.error(f"[{self._agent_name}] خطأ في معالجة الحدث: {e}")

    async def _dispatch(self, event: BusinessEvent) -> None:
        """توزيع الحدث على المعالجات المسجَّلة."""
        # تجاهل الأحداث الصادرة من هذا الوكيل نفسه
        if event["source"] == self._agent_name:
            return

        # تجاهل الأحداث الموجَّهة لوكيل آخر
        if event["target"] and event["target"] != self._agent_name:
            return

        handlers = self._handlers.get(event["event_type"], [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"[{self._agent_name}] خطأ في المعالج: {handler.__name__}: {e}")

    # ── النبضات (Heartbeat) ──────────────────────────────

    async def send_heartbeat(self, status: str = "healthy") -> None:
        """إرسال نبضة حياة — يُستدعى كل 30 ثانية."""
        key = self.HEARTBEAT_KEY.format(agent=self._agent_name)
        data = json.dumps({
            "agent":     self._agent_name,
            "status":    status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)
        await self._pub.setex(key, 60, data)  # TTL 60 ثانية

    async def get_agent_status(self, agent: AgentName) -> Optional[Dict]:
        """قراءة حالة وكيل آخر."""
        key = self.HEARTBEAT_KEY.format(agent=agent)
        data = await self._pub.get(key)
        return json.loads(data) if data else None

    async def get_all_agents_status(self) -> Dict[AgentName, Optional[Dict]]:
        """قراءة حالة جميع الوكلاء."""
        result = {}
        for agent in AgentName:
            result[agent] = await self.get_agent_status(agent)
        return result

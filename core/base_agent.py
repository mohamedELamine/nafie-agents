"""
core/base_agent.py
==================
الفئة الأساسية التي يرثها كل وكيل.
توفر: الاتصال بـ Redis · النبضات · المراقبة · معالجة الأخطاء.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from langsmith import Client as LangSmithClient

from core.redis_bus import RedisBus
from core.state import AgentName, BusinessEvent, EventType

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    الفئة الأساسية لكل وكيل في المنظومة.

    كل وكيل يجب أن:
    ١. يعرّف اسمه (agent_name)
    ٢. ينفّذ setup_handlers() لتسجيل معالجات الأحداث
    ٣. ينفّذ run() لتشغيل منطق LangGraph الخاص به
    """

    agent_name: AgentName  # يُعرِّفه كل وكيل في الفئة الفرعية

    def __init__(self):
        self.bus = RedisBus(os.getenv("REDIS_URL", "redis://localhost:6379"))
        self.ls_client = LangSmithClient()
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── الدورة الحياتية ──────────────────────────────────

    async def start(self) -> None:
        """تشغيل الوكيل: اتصال + معالجات + استماع + نبضات."""
        await self.bus.connect(self.agent_name)
        await self.setup_handlers()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"[{self.agent_name}] ✓ جاهز")
        await self.bus.listen()

    async def stop(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        await self.bus.disconnect()
        logger.info(f"[{self.agent_name}] ✓ توقّف")

    # ── المجردات — يجب التنفيذ في كل وكيل ──────────────

    @abstractmethod
    async def setup_handlers(self) -> None:
        """تسجيل معالجات أحداث Redis."""
        ...

    @abstractmethod
    async def run(self, event: BusinessEvent) -> None:
        """تنفيذ منطق LangGraph عند وصول حدث."""
        ...

    # ── أدوات مساعدة مشتركة ──────────────────────────────

    async def emit(self, event_type: EventType, payload: dict,
                   target: Optional[AgentName] = None, priority: int = 5,
                   trace_id: Optional[str] = None) -> str:
        """اختصار لنشر حدث."""
        return await self.bus.publish(event_type, payload, target, priority, trace_id)

    async def emit_error(self, error: str, context: dict = None,
                         trace_id: str = None) -> None:
        """نشر حدث خطأ للمشرف."""
        from core.state import AgentName as AN
        await self.emit(
            EventType.SUPERVISOR_ALERT,
            {"error": error, "context": context or {}, "agent": self.agent_name},
            target=AN.SUPERVISOR,
            priority=1,
            trace_id=trace_id,
        )
        logger.error(f"[{self.agent_name}] ✗ {error}")

    # ── النبضات ──────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await self.bus.send_heartbeat("healthy")
            except Exception as e:
                logger.warning(f"[{self.agent_name}] فشل النبضة: {e}")
            await asyncio.sleep(30)

    # ── المراقبة ─────────────────────────────────────────

    def trace_run(self, run_name: str, inputs: dict):
        """فتح Trace في LangSmith."""
        return self.ls_client.create_run(
            name=f"{self.agent_name}.{run_name}",
            inputs=inputs,
            run_type="chain",
        )

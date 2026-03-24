from __future__ import annotations

import json
import os
import sys
import types
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

try:
    import psycopg2
except ImportError:  # pragma: no cover - integration dependency only
    psycopg2 = None

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover - integration dependency only
    redis_lib = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


if "langsmith" not in sys.modules:
    langsmith_stub = types.ModuleType("langsmith")
    langsmith_stub.Client = lambda *args, **kwargs: SimpleNamespace(
        create_run=lambda **run_kwargs: None
    )
    sys.modules["langsmith"] = langsmith_stub


class RedisBus:
    """Integration Redis bus backed by a real Redis instance with a test prefix."""

    def __init__(self, redis_url: str, prefix: str = "test:"):
        if redis_lib is None:  # pragma: no cover - handled by fixture skip
            raise RuntimeError("redis package is not installed")
        self.redis_url = redis_url
        self.prefix = prefix
        self.client = redis_lib.from_url(redis_url, decode_responses=True)
        self.agent_name: Optional[str] = None

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _dump(self, payload: Dict[str, Any]) -> str:
        return json.dumps(payload, default=self._serialize)

    def _key(self, name: str) -> str:
        return f"{self.prefix}{name}"

    def cleanup(self) -> None:
        keys = list(self.client.scan_iter(match=f"{self.prefix}*"))
        if keys:
            self.client.delete(*keys)

    async def connect(self, agent_name=None) -> None:
        self.agent_name = (
            agent_name.value if isinstance(agent_name, Enum) else agent_name
        )

    async def disconnect(self) -> None:
        return None

    def on(self, *args, **kwargs) -> None:
        return None

    async def listen(self) -> None:  # pragma: no cover - not used in these tests
        raise RuntimeError("Integration fixture does not implement the listen loop")

    async def send_heartbeat(self, status: str = "healthy") -> None:
        if self.agent_name:
            self.client.setex(self._key(f"heartbeat:{self.agent_name}"), 60, status)

    def publish_trigger(self, stream: str, event: Dict[str, Any]) -> str:
        return self.publish_stream(stream, event)

    def publish_stream(self, stream: str, event: Dict[str, Any]) -> str:
        return self.client.xadd(self._key(stream), {"data": self._dump(event)})

    def read_stream(self, stream: str) -> list[Dict[str, Any]]:
        messages: list[Dict[str, Any]] = []
        for message_id, fields in self.client.xrange(self._key(stream)):
            if "data" not in fields:
                continue
            payload = json.loads(fields["data"])
            payload["__message_id"] = message_id
            messages.append(payload)
        return messages

    def read_supervisor_stream(self, channel: str) -> list[Dict[str, Any]]:
        messages: list[Dict[str, Any]] = []
        for message_id, fields in self.client.xrange(self._key(f"streams:{channel}")):
            if "payload" not in fields:
                continue
            payload = json.loads(fields["payload"])
            payload["__message_id"] = message_id
            messages.append(payload)
        return messages

    def build_business_event(
        self,
        event_type,
        payload: Dict[str, Any],
        source,
        target=None,
        priority: int = 5,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "source": source,
            "target": target,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id or uuid.uuid4().hex,
            "priority": priority,
        }

    def _stream_for_event(self, event_type) -> str:
        value = event_type.value if isinstance(event_type, Enum) else str(event_type)
        mapping = {
            "content.ready": "content-events",
            "marketing.campaign.sent": "marketing-events",
            "support.ticket.resolved": "support-events",
            "supervisor.alert": "supervisor-events",
            "analytics.anomaly.detected": "analytics:signals",
        }
        return mapping.get(value, "misc-events")

    async def publish(
        self,
        event_type,
        payload: Dict[str, Any],
        target=None,
        priority: int = 5,
        trace_id: Optional[str] = None,
    ) -> str:
        event = self.build_business_event(
            event_type=event_type,
            payload=payload,
            source=self.agent_name or "integration-test",
            target=target,
            priority=priority,
            trace_id=trace_id,
        )
        self.publish_stream(self._stream_for_event(event_type), event)
        return event["event_id"]

    async def ensure_consumer_group(
        self, channel: str, group: str, consumer: str = "default"
    ) -> bool:
        stream = self._key(f"streams:{channel}")
        if not self.client.exists(stream):
            self.client.xadd(stream, {"payload": self._dump({"init": True})})
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis_lib.exceptions.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        return True

    async def publish_supervisor_event(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> bool:
        envelope = {
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "data": data,
            "correlation_id": correlation_id or uuid.uuid4().hex,
            "causation_id": causation_id or uuid.uuid4().hex,
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.client.xadd(
            self._key(f"streams:{channel}"),
            {"payload": self._dump(envelope)},
        )
        return True

    async def read_group(
        self, channel: str, group: str, consumer: str, count: int = 1
    ) -> Optional[Dict[str, Any]]:
        await self.ensure_consumer_group(channel, group, consumer)
        stream = self._key(f"streams:{channel}")
        result = self.client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=100,
        )
        if not result:
            return None

        message_id, fields = result[0][1][0]
        payload = json.loads(fields.get("payload", "{}"))
        return {"id": message_id, "data": payload}

    async def ack(self, channel: str, group: str, message_id: str) -> bool:
        stream = self._key(f"streams:{channel}")
        self.client.xack(stream, group, message_id)
        return True


@pytest.fixture
def redis_bus():
    if redis_lib is None:
        pytest.skip("redis package is not installed")

    bus = RedisBus(redis_url="redis://localhost:6379/0", prefix="test:")
    try:
        bus.client.ping()
    except Exception as exc:  # pragma: no cover - depends on local services
        pytest.skip(f"Redis is not available: {exc}")

    bus.cleanup()
    try:
        yield bus
    finally:
        bus.cleanup()
        bus.client.close()


@pytest.fixture
def db_conn():
    if psycopg2 is None:
        pytest.skip("psycopg2 is not installed")

    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL is not set")

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:  # pragma: no cover - depends on local services
        pytest.skip(f"Test database is not available: {exc}")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        yield conn
    finally:
        conn.rollback()
        conn.close()

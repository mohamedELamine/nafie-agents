import asyncio
import json
import os
import sys
import time
import types
import uuid
from urllib.parse import urlparse

import redis.asyncio as redis
from dotenv import load_dotenv
from redis.exceptions import ResponseError

from core.contracts import (
    EVENT_NEW_PRODUCT_LIVE,
    EVENT_THEME_APPROVED,
    STREAM_PRODUCT_EVENTS,
)

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_pkg = types.ModuleType("visual_production_agent")
_pkg.__path__ = [_AGENT_DIR]
_pkg.__package__ = "visual_production_agent"
sys.modules.setdefault("visual_production_agent", _pkg)

from visual_production_agent.agent import build_visual_agent, run_visual_pipeline
from visual_production_agent.db.connection import close_pool, init_pool
from visual_production_agent.logging_config import configure_logging, get_logger

load_dotenv()
configure_logging()

logger = get_logger(__name__)

CONSUMER_GROUP = "visual-production-agent"
CONSUMER_NAME = "visual-production-worker-1"
DEDUP_TTL_SECONDS = 120
_recent_launches: dict[str, float] = {}


def _redis_client() -> redis.Redis:
    parsed = urlparse(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    db = int((parsed.path or "/0").lstrip("/") or "0")
    return redis.Redis(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        db=db,
        decode_responses=True,
    )


def _owner_email() -> str:
    return os.getenv("VISUAL_OWNER_EMAIL") or os.getenv("OWNER_EMAIL", "admin@example.com")


def _build_theme_contract(event: dict) -> dict:
    data = event.get("data") or {}
    contract = dict(data.get("theme_contract") or {})
    slug = contract.get("slug") or data.get("theme_slug") or event.get("theme_slug") or "unknown-theme"
    version = contract.get("version") or data.get("version") or event.get("version") or "1.0.0"
    contract.setdefault("slug", slug)
    contract.setdefault("version", version)
    contract.setdefault("domain", data.get("theme_name") or event.get("theme_name") or slug)
    contract.setdefault("cluster", "wordpress-theme")
    contract.setdefault("colors", ["#1f4b99", "#f5f1e8"])
    contract.setdefault("features", ["rtl", "woocommerce", "responsive"])
    return contract


def _dedupe_key(event: dict, theme_contract: dict) -> str:
    return event.get("correlation_id") or f"{theme_contract['slug']}:{theme_contract['version']}"


def _should_skip_launch(event: dict, theme_contract: dict) -> bool:
    now = time.monotonic()
    expired = [key for key, seen_at in _recent_launches.items() if now - seen_at > DEDUP_TTL_SECONDS]
    for key in expired:
        _recent_launches.pop(key, None)
    key = _dedupe_key(event, theme_contract)
    if key in _recent_launches:
        return True
    _recent_launches[key] = now
    return False


async def _ensure_group(client: redis.Redis) -> None:
    if not await client.exists(STREAM_PRODUCT_EVENTS):
        await client.xadd(STREAM_PRODUCT_EVENTS, {"init": "true"})
    try:
        await client.xgroup_create(STREAM_PRODUCT_EVENTS, CONSUMER_GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _handle_event(agent, event: dict) -> None:
    event_type = event.get("event_type")
    if event_type not in {EVENT_THEME_APPROVED, EVENT_NEW_PRODUCT_LIVE}:
        return
    theme_contract = _build_theme_contract(event)
    if _should_skip_launch(event, theme_contract):
        logger.info("Skipping duplicate %s for %s", event_type, theme_contract["slug"])
        return
    batch_id = f"{theme_contract['slug']}_{uuid.uuid4().hex[:8]}"
    result = await run_visual_pipeline(
        agent=agent,
        theme_contract=theme_contract,
        batch_id=batch_id,
        version=theme_contract["version"],
        owner_email=_owner_email(),
    )
    logger.info("Processed %s for %s -> %s", event_type, theme_contract["slug"], result.get("status"))


async def _listen(client: redis.Redis, agent) -> None:
    while True:
        messages = await client.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername=CONSUMER_NAME,
            streams={STREAM_PRODUCT_EVENTS: ">"},
            count=5,
            block=2000,
        )
        for _, stream_messages in messages:
            for message_id, fields in stream_messages:
                try:
                    event = json.loads(fields.get("data", "{}"))
                    await _handle_event(agent, event)
                except Exception as exc:
                    logger.error("visual listener error for %s: %s", message_id, exc)
                finally:
                    await client.xack(STREAM_PRODUCT_EVENTS, CONSUMER_GROUP, message_id)


async def main() -> None:
    logger.info("Visual Production Agent starting...")
    init_pool()
    client = _redis_client()
    agent = build_visual_agent()
    try:
        await _ensure_group(client)
        logger.info("Waiting for %s / %s events...", EVENT_THEME_APPROVED, EVENT_NEW_PRODUCT_LIVE)
        await _listen(client, agent)
    finally:
        await client.aclose()
        close_pool()


if __name__ == "__main__":
    asyncio.run(main())

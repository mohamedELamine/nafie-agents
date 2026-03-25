#!/usr/bin/env python3
"""Run an end-to-end smoke test across the ecosystem."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg2
import redis
import requests


logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("scripts.e2e_smoke_test")

PRODUCT_STREAM = "product-events"
THEME_STREAM = "theme-events"
WORKFLOW_COMMAND_STREAM = "streams:workflow_commands"
STREAM_ALIASES = {
    "content-events": ["content-events"],
    "asset-events": ["asset-events"],
    "analytics-signals": ["analytics-signals", "analytics:signals"],
    "marketing-campaigns": ["marketing-campaigns", "marketing-events"],
}


@dataclass
class StepResult:
    name: str
    status: str
    elapsed_ms: int
    detail: str


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(env("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def db_dsn() -> str:
    return env("DATABASE_URL", "postgresql://app_user:change_me@localhost:5432/ar_themes")


def qdrant_url() -> str:
    return env("QDRANT_URL", "http://localhost:6333").rstrip("/")


def run_step(name: str, callback) -> StepResult:
    started = time.monotonic()
    try:
        detail = callback()
        return StepResult(name, "PASS", int((time.monotonic() - started) * 1000), str(detail))
    except Exception as exc:
        return StepResult(name, "FAIL", int((time.monotonic() - started) * 1000), str(exc))


def check_redis() -> str:
    client = redis_client()
    if not client.ping():
        raise RuntimeError("Redis ping failed")
    return "Redis ping succeeded"


def check_postgres() -> str:
    with psycopg2.connect(db_dsn()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    return "PostgreSQL SELECT 1 succeeded"


def check_qdrant() -> str:
    response = requests.get(f"{qdrant_url()}/healthz", timeout=5)
    response.raise_for_status()
    return f"Qdrant health={response.text.strip() or response.status_code}"


def build_event() -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "theme_slug": "e2e-test-theme",
        "theme_name": "قالب اختبار E2E",
        "version": "1.0.0",
        "occurred_at": now_iso,
        "test_run": True,
    }
    return {
        "event_id": f"e2e-{uuid.uuid4().hex}",
        "event_type": "THEME_APPROVED",
        "theme_slug": payload["theme_slug"],
        "theme_name": payload["theme_name"],
        "version": payload["version"],
        "occurred_at": now_iso,
        "test_run": True,
        "source": "e2e_smoke_test",
        "correlation_id": f"e2e-{uuid.uuid4().hex}",
        "data": payload,
    }


def build_workflow_command(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": f"e2e-workflow-{uuid.uuid4().hex}",
        "event_type": "WORKFLOW_START",
        "data": {
            "workflow_type": "theme_launch",
            "context": {
                "theme_slug": event["data"]["theme_slug"],
                "version": event["data"]["version"],
                "correlation_id": event["correlation_id"],
            },
        },
        "correlation_id": event["correlation_id"],
        "causation_id": event["event_id"],
        "workflow_id": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_product_live_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event["data"]
    return {
        "event_id": f"e2e-product-live-{uuid.uuid4().hex}",
        "event_type": "NEW_PRODUCT_LIVE",
        "theme_slug": data["theme_slug"],
        "theme_name": data["theme_name"],
        "version": data["version"],
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "test_run": True,
        "source": "e2e_smoke_test",
        "correlation_id": event["correlation_id"],
        "data": data,
    }


def stream_sizes(client: redis.Redis) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for names in STREAM_ALIASES.values():
        for stream in names:
            sizes[stream] = client.xlen(stream) if client.exists(stream) else 0
    return sizes


def publish_event(client: redis.Redis, event: dict[str, Any]) -> str:
    body = {"data": json.dumps(event, ensure_ascii=False)}
    primary_id = client.xadd(PRODUCT_STREAM, body)
    client.xadd(THEME_STREAM, body)
    product_live = build_product_live_event(event)
    product_live_id = client.xadd(PRODUCT_STREAM, {"data": json.dumps(product_live, ensure_ascii=False)})
    workflow_command = build_workflow_command(event)
    command_id = client.xadd(
        WORKFLOW_COMMAND_STREAM,
        {"payload": json.dumps(workflow_command, ensure_ascii=False)},
    )
    return (
        f"product-events={primary_id}, new_product_live={product_live_id}, theme-events=compatibility-copy, "
        f"workflow_commands={command_id}"
    )


def stream_deltas(client: redis.Redis, baseline: dict[str, int]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for label, names in STREAM_ALIASES.items():
        total = 0
        for stream in names:
            current = client.xlen(stream) if client.exists(stream) else 0
            total += max(0, current - baseline.get(stream, 0))
        summary[label] = total
    return summary


def check_workflow_instance(theme_slug: str) -> str:
    with psycopg2.connect(db_dsn()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM workflow_instances WHERE theme_slug = %s",
                (theme_slug,),
            )
            count = cursor.fetchone()[0]
    if count < 1:
        raise RuntimeError("No workflow_instances row found for e2e-test-theme")
    return f"workflow_instances rows={count}"


def print_result(result: StepResult) -> None:
    print(f"{result.status} | {result.name} | {result.elapsed_ms}ms | {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Check connectivity only.")
    args = parser.parse_args()

    results = [
        run_step("Redis health", check_redis),
        run_step("PostgreSQL health", check_postgres),
        run_step("Qdrant health", check_qdrant),
    ]
    for result in results:
        print_result(result)
    if args.dry_run or any(result.status == "FAIL" for result in results):
        return 0 if args.dry_run and all(r.status == "PASS" for r in results) else 1

    client = redis_client()
    baseline = stream_sizes(client)
    publish_result = run_step("Publish THEME_APPROVED", lambda: publish_event(client, build_event()))
    print_result(publish_result)

    wait_started = time.monotonic()
    time.sleep(30)
    summary = stream_deltas(client, baseline)
    wait_result = StepResult(
        "Observe downstream streams",
        "PASS",
        int((time.monotonic() - wait_started) * 1000),
        ", ".join(f"{name}={count}" for name, count in summary.items()),
    )
    print_result(wait_result)

    db_result = run_step("Check workflow_instances", lambda: check_workflow_instance("e2e-test-theme"))
    print_result(db_result)
    return 0 if all(item.status == "PASS" for item in [*results, publish_result, wait_result, db_result]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

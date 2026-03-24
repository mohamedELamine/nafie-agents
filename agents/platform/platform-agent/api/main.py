"""
FastAPI Application — T080–T084
Endpoints: /webhooks/lemonsqueezy, /health, /review/{key}, /assets/{key}/decision
"""
from __future__ import annotations
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from commerce.webhook_handler import CommerceEventConsumer
from db.connection import init_pool, close_pool, get_conn
from db.registry import ProductRegistry
from logging_config import configure_logging
from services.redis_bus import RedisBus
from services.resend_client import ResendClient
from api.background import TimeoutWatchdog

logger = logging.getLogger("platform_agent.api")

# ── Services (singleton) ────────────────────────────────────
_redis_bus: Optional[RedisBus] = None
_registry: Optional[ProductRegistry] = None
_consumer: Optional[CommerceEventConsumer] = None
_watchdog: Optional[TimeoutWatchdog] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """تهيئة الـ services عند البدء."""
    configure_logging()
    global _redis_bus, _registry, _consumer, _watchdog

    init_pool()
    _redis_bus = RedisBus()
    _registry = ProductRegistry(get_conn)
    _consumer = CommerceEventConsumer(_redis_bus)
    resend = ResendClient()
    _watchdog = TimeoutWatchdog(get_conn, resend)
    _watchdog.start()

    logger.info("Platform Agent API started ✅")
    yield
    _watchdog.stop()
    _redis_bus.close()
    close_pool()


app = FastAPI(
    title="Platform Agent API",
    description="وكيل المنصة — نافع",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Middleware: Request Logging + trace_id ─────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "HTTP | %s %s | status=%s | %.1fms | trace=%s",
        request.method, request.url.path,
        response.status_code, duration, trace_id,
    )
    response.headers["X-Trace-ID"] = trace_id
    return response


# ── Error Handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error | %s | %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error_code": "PLT_500", "message": "Internal server error"},
    )


# ── T081 — Health Check ───────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": "platform",
        "version": "1.0.0",
    }


# ── T080 — Lemon Squeezy Webhook ─────────────────────────
@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(None, alias="X-Signature"),
):
    if not x_signature:
        raise HTTPException(status_code=400, detail="X-Signature header missing")

    payload = await request.body()

    try:
        _consumer.handle_webhook(payload, x_signature)
    except PermissionError as exc:
        error_code = str(exc).split(":")[0]
        logger.warning("webhook | PLT_1001 | invalid signature")
        raise HTTPException(status_code=403, detail={"error_code": error_code, "message": str(exc)})
    except Exception as exc:
        logger.error("webhook | processing failed | %s", exc)
        raise HTTPException(status_code=500, detail={"error_code": "PLT_500", "message": str(exc)})

    return {"status": "ok"}


# ── T082 — Human Review Endpoint ─────────────────────────
class ReviewRequest(BaseModel):
    decision: str     # approved_as_is | approved_with_edits | needs_revision_minor | needs_revision_major | rejected
    notes: Optional[str] = ""
    edits: Optional[Dict[str, Any]] = None


@app.post("/review/{idempotency_key}")
async def submit_review(idempotency_key: str, body: ReviewRequest):
    """يستقبل قرار المراجعة البشرية ويُخزّنه في Redis لاستئناف الـ workflow."""
    valid_decisions = {
        "approved_as_is", "approved_with_edits",
        "needs_revision_minor", "needs_revision_major", "rejected",
    }
    if body.decision not in valid_decisions:
        raise HTTPException(status_code=422, detail=f"decision يجب أن يكون: {valid_decisions}")

    # التحقق من وجود الـ workflow
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM execution_log WHERE idempotency_key=%s AND node_name='HUMAN_REVIEW_GATE' AND status='started' LIMIT 1",
                (idempotency_key,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail={"error_code": "PLT_404",
                                                              "message": "Workflow not found or not awaiting review"})

    # تخزين القرار في Redis
    review_data = json.dumps({"decision": body.decision, "notes": body.notes, "edits": body.edits or {}})
    _redis_bus._redis.setex(f"review:{idempotency_key}", 3600, review_data)

    logger.info("submit_review | key=%s decision=%s", idempotency_key, body.decision)
    return {"status": "ok", "workflow_resumed": True}


# ── T083 — Asset Decision Endpoint ────────────────────────
class AssetDecisionRequest(BaseModel):
    decision: str  # proceed_with_available | extend_wait | cancel

@app.post("/assets/{idempotency_key}/decision")
async def asset_decision(idempotency_key: str, body: AssetDecisionRequest):
    valid = {"proceed_with_available", "extend_wait", "cancel"}
    if body.decision not in valid:
        raise HTTPException(status_code=422, detail=f"decision يجب أن يكون: {valid}")

    # تخزين القرار
    _redis_bus._redis.setex(
        f"asset_decision:{idempotency_key}",
        86400,
        body.decision,
    )
    logger.info("asset_decision | key=%s decision=%s", idempotency_key, body.decision)
    return {"status": "ok", "decision": body.decision}

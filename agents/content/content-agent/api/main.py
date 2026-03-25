"""
FastAPI — وكيل المحتوى
Endpoints: GET /health، POST /review/{key}
المرجع: spec.md § ٢٢
"""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.content_registry import ContentRegistry
from listeners.content_listener import ContentListener
from logging_config import configure_logging, get_logger
from services.redis_bus import RedisBus
from services.resend_client import ContentResendClient

configure_logging()
logger = get_logger("api.main")

# ── Shared Services ────────────────────────────────────────────────
_registry: Optional[ContentRegistry]      = None
_redis:    Optional[RedisBus]             = None
_resend:   Optional[ContentResendClient]  = None
_listener: Optional[ContentListener]      = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _registry, _redis, _resend, _listener

    _registry = ContentRegistry()
    _redis    = RedisBus()
    _resend   = ContentResendClient()
    _listener = ContentListener(
        redis_bus = _redis,
        registry  = _registry,
        resend    = _resend,
    )

    import threading
    t = threading.Thread(target=_listener.start, daemon=True)
    t.start()

    logger.info("content_agent.started")
    yield

    if _listener:
        _listener.stop()
    if _registry:
        _registry.close()
    if _redis:
        _redis.close()
    logger.info("content_agent.stopped")


app = FastAPI(
    title       = "Content Agent — نافع",
    description = "وكيل إنتاج المحتوى العربي",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)


# ── Middleware: Trace ID ───────────────────────────────────────────

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4())[:8])
    logger.info("http.request method=%s path=%s trace=%s", request.method, request.url.path, trace_id)
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "agent": "content", "version": "1.0.0"}


class ReviewDecision(BaseModel):
    decision: str   # "approved" | "rejected"
    notes:    Optional[str] = None


@app.post("/review/{review_key}")
def submit_review(review_key: str, body: ReviewDecision):
    """
    يستقبل قرار المراجعة البشرية.
    decision: "approved" | "rejected"
    """
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision يجب أن يكون approved أو rejected")

    if not _registry:
        raise HTTPException(status_code=503, detail="Registry غير جاهز")

    item = _registry.get_review_item(review_key)
    if not item:
        raise HTTPException(status_code=404, detail=f"review_key غير موجود أو تم البت فيه: {review_key}")

    _registry.record_review_decision(
        review_key = review_key,
        decision   = body.decision,
        notes      = body.notes,
    )

    logger.info("review.decision key=%s decision=%s", review_key, body.decision)

    # إشعار بالنتيجة
    if _redis:
        event = _redis.build_event(
            event_type     = "CONTENT_REVIEW_DECIDED",
            data           = {
                "review_key":  review_key,
                "content_id":  item.get("content_id"),
                "content_type": item.get("content_type"),
                "decision":    body.decision,
                "notes":       body.notes,
            },
            correlation_id = item.get("correlation_id", ""),
        )
        _redis.publish("content-events", event)

    return {"status": "recorded", "review_key": review_key, "decision": body.decision}

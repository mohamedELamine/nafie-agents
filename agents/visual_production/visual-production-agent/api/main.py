"""
Visual-production-agent FastAPI application.
"""
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the agent root is on sys.path for `uvicorn api.main:app`.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import (
    close_pool,
    get_conn,
    get_manifest,
    init_pool,
    update_manifest_status,
)
from logging_config import get_logger

logger = get_logger("api.main")

VALID_REVIEW_DECISIONS = {"approved", "rejected", "needs_revision"}


async def _get_review_checkpoint(redis_bus, batch_key: str) -> Dict[str, Any]:
    checkpoint = await redis_bus.checkpoint_get(f"visual_review:{batch_key}")
    if not checkpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Review checkpoint for batch {batch_key!r} not found",
        )
    return checkpoint


async def _finalize_non_approved_review(redis_bus, batch_key: str, status: str, notes: str) -> None:
    with get_conn() as conn:
        update_manifest_status(conn, batch_key, status=status, notes=notes or None)
    await redis_bus.checkpoint_delete(f"visual_review:{batch_key}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup, release on shutdown."""
    logger.info("Starting visual-production-agent API…")
    init_pool()
    yield
    close_pool()
    logger.info("Visual-production-agent API shut down.")


app = FastAPI(
    title="Visual Production Agent API",
    description="API for visual asset generation and management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — do NOT combine allow_origins=["*"] with allow_credentials=True
# (browsers reject it). Use explicit origins when credentials are needed.
_CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> Dict[str, Any]:
    from datetime import datetime, timezone
    return {
        "service": "visual-production-agent",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "service": "visual-production-agent"}


# ---------------------------------------------------------------------------
# Review decision endpoint
# ---------------------------------------------------------------------------

@app.post("/review/{batch_key}")
async def handle_review_decision(
    batch_key: str, decision: Dict[str, str]
) -> Dict[str, Any]:
    """
    Handle visual review decision.
    decision.decision: "approved" | "rejected" | "needs_revision"
    decision.notes:    optional string
    """
    decision_type = decision.get("decision", "").lower()
    notes = decision.get("notes", "")

    if decision_type not in VALID_REVIEW_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision type: {decision_type!r}",
        )

    logger.info(f"Review decision for {batch_key}: {decision_type}")

    from agent import build_visual_agent, complete_approved_pipeline

    agent = build_visual_agent()
    checkpoint = await _get_review_checkpoint(agent.redis, batch_key)

    if decision_type == "approved":
        result = await complete_approved_pipeline(
            agent=agent,
            batch_id=batch_key,
            theme_slug=checkpoint.get("theme_slug", ""),
            version=checkpoint.get("version", "1.0"),
            processed_result={
                "processed": checkpoint.get("assets", {}),
                "total_size_kb": checkpoint.get("total_size_kb", 0),
            },
            owner_email=checkpoint.get("owner_email", ""),
        )
        await agent.redis.checkpoint_delete(f"visual_review:{batch_key}")
        return {
            "status": decision_type,
            "batch_key": batch_key,
            "message": "Batch approved and published",
            "result": result,
        }

    await _finalize_non_approved_review(
        agent.redis,
        batch_key,
        status=decision_type,
        notes=notes,
    )
    return {
        "status": decision_type,
        "batch_key": batch_key,
        "message": f"Batch {decision_type}",
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Manifest endpoint
# ---------------------------------------------------------------------------

@app.get("/assets/{batch_key}/manifest")
async def get_batch_manifest(batch_key: str) -> Dict[str, Any]:
    """Fetch the asset manifest for a batch from the database."""
    try:
        with get_conn() as conn:
            manifest = get_manifest(conn, batch_key)

        if not manifest:
            raise HTTPException(status_code=404, detail=f"Batch {batch_key!r} not found")

        return manifest

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching manifest {batch_key}: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ---------------------------------------------------------------------------
# Manual pipeline trigger
# ---------------------------------------------------------------------------

@app.post("/visual/pipeline")
async def run_visual_pipeline_endpoint(request: Request) -> Dict[str, Any]:
    """Manually trigger visual pipeline for a theme."""
    try:
        body = await request.json()
        theme_contract = body.get("theme_contract", {})
        if not theme_contract:
            raise HTTPException(status_code=400, detail="theme_contract is required")

        version = theme_contract.get("version", "1.0")
        owner_email = body.get("owner_email") or os.environ.get(
            "VISUAL_OWNER_EMAIL", "admin@example.com"
        )
        batch_id = f"manual_{uuid.uuid4().hex[:8]}"

        logger.info(f"Manual pipeline triggered — batch {batch_id}")

        from agent import build_visual_agent, run_visual_pipeline

        agent = build_visual_agent()
        result = await run_visual_pipeline(
            agent=agent,
            theme_contract=theme_contract,
            batch_id=batch_id,
            version=version,
            owner_email=owner_email,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

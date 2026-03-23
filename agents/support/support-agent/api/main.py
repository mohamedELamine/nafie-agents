"""
Support-agent FastAPI application.
Handles HelpScout and Facebook webhooks, runs the LangGraph pipeline.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from ..agent import run_support_pipeline
from ..db.connection import close_pool, init_pool
from ..logging_config import get_logger
from ..services import (
    get_claude_client,
    get_facebook_client,
    get_helpscout_client,
    get_qdrant_client,
    get_redis_bus,
    ResendClient,
)

logger = get_logger("api.main")

# ---------------------------------------------------------------------------
# Application-level service instances (initialised in lifespan)
# ---------------------------------------------------------------------------
_services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup, release on shutdown."""
    logger.info("Starting support-agent API…")

    # DB connection pool
    init_pool()

    # Service clients
    _services["helpscout"] = get_helpscout_client()
    _services["claude"] = get_claude_client()
    _services["qdrant"] = get_qdrant_client()
    _services["redis"] = get_redis_bus()
    _services["facebook"] = get_facebook_client()
    _services["resend"] = ResendClient()

    logger.info("All services initialised.")
    yield

    # Shutdown
    close_pool()
    logger.info("Support-agent API shut down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Support Agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"service": "support-agent", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------

@app.post("/webhooks/helpscout")
async def handle_helpscout_webhook(request: Request):
    try:
        data = await request.json()
        ticket_data = data.get("data", {})
        ticket_id = ticket_data.get("id") or ticket_data.get("ticket_id")

        if not ticket_id:
            raise HTTPException(status_code=400, detail="Missing ticket ID")

        logger.info(f"HelpScout webhook — ticket {ticket_id}")

        # Normalise for the pipeline
        ticket_data.setdefault("ticket_id", ticket_id)
        ticket_data.setdefault("platform", "helpscout")

        result = run_support_pipeline(
            ticket_data=ticket_data,
            helpscout_client=_services["helpscout"],
            claude_client=_services["claude"],
            qdrant_client=_services["qdrant"],
            resend_client=_services["resend"],
            redis_bus=_services["redis"],
        )

        return JSONResponse(
            status_code=200,
            content={"status": "received", "ticket_id": ticket_id, "success": result.get("success", True)},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing HelpScout webhook: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.post("/webhooks/facebook")
async def handle_facebook_webhook(request: Request):
    try:
        data = await request.json()
        ticket_data = data.get("data", {})
        comment_id = ticket_data.get("id") or ticket_data.get("conversation_id")

        if not comment_id:
            raise HTTPException(status_code=400, detail="Missing comment ID")

        logger.info(f"Facebook webhook — comment {comment_id}")

        ticket_data.setdefault("ticket_id", comment_id)
        ticket_data.setdefault("platform", "facebook")

        result = run_support_pipeline(
            ticket_data=ticket_data,
            helpscout_client=_services["helpscout"],
            claude_client=_services["claude"],
            qdrant_client=_services["qdrant"],
            resend_client=_services["resend"],
            redis_bus=_services["redis"],
            facebook_client=_services["facebook"],
        )

        return JSONResponse(
            status_code=200,
            content={"status": "received", "comment_id": comment_id, "success": result.get("success", True)},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Facebook webhook: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..db import marketing_calendar, campaign_log
from ..db.connection import close_pool, get_conn, init_pool
from ..logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger("api.main")


class CampaignCreate(BaseModel):
    title: str
    theme_slug: str
    start_date: datetime
    end_date: datetime


class CampaignStatusResponse(BaseModel):
    campaign_id: str
    status: str
    start_date: datetime
    end_date: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager — initialise DB pool on startup, release on shutdown."""
    init_pool(minconn=2, maxconn=10)
    logger.info("Marketing agent started")
    yield
    close_pool()
    logger.info("Marketing agent stopped")


app = FastAPI(
    title="Marketing Agent API",
    description="API for the marketing agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ── Campaigns ─────────────────────────────────────────────────────────────────

@app.post("/campaigns", response_model=CampaignStatusResponse)
async def create_campaign(campaign: CampaignCreate) -> Dict[str, Any]:
    """Create a new marketing campaign."""
    try:
        campaign_id = f"campaign_{int(datetime.utcnow().timestamp())}"

        campaign_data = {
            "campaign_id": campaign_id,
            "title": campaign.title,
            "theme_slug": campaign.theme_slug,
            "content_snapshot": {},
            "assets_snapshot": {},
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "status": "draft",
        }

        log_entry = {
            "log_id": f"log_{int(datetime.utcnow().timestamp())}",
            "campaign_id": campaign_id,
            "event_type": "CAMPAIGN_CREATED",
            "details": {"title": campaign.title, "theme_slug": campaign.theme_slug},
        }

        with get_conn() as conn:
            marketing_calendar.save_campaign(conn, campaign_data)
            campaign_log.save_log(conn, log_entry)

        logger.info(f"Created campaign: {campaign_id}")
        return campaign_data

    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaigns/{campaign_id}", response_model=CampaignStatusResponse)
async def get_campaign(campaign_id: str) -> Dict[str, Any]:
    """Get campaign by ID."""
    try:
        with get_conn() as conn:
            campaign = marketing_calendar.get_campaign_by_id(conn, campaign_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campaigns/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: str) -> Dict[str, Any]:
    """Start the marketing pipeline for a campaign."""
    try:
        from ..agent import run_marketing_pipeline
        from ..state import MarketingState
        from ..models import Campaign

        with get_conn() as conn:
            campaign_data = marketing_calendar.get_campaign_by_id(conn, campaign_id)

        if not campaign_data:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Build a Campaign dataclass from DB row
        campaign_obj = Campaign(
            campaign_id=campaign_data["campaign_id"],
            title=campaign_data["title"],
            theme_slug=campaign_data["theme_slug"],
            content_snapshot=campaign_data.get("content_snapshot") or {},
            assets_snapshot=campaign_data.get("assets_snapshot") or {},
            start_date=campaign_data["start_date"],
            end_date=campaign_data["end_date"],
            status=campaign_data.get("status", "draft"),
        )

        # Build initial MarketingState and run pipeline
        state = MarketingState(current_campaign=campaign_obj)
        result = run_marketing_pipeline(state)

        logger.info(f"Started marketing pipeline for campaign: {campaign_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule/{campaign_id}/cancel")
async def cancel_schedule(campaign_id: str) -> Dict[str, str]:
    """Cancel scheduled posts for a campaign."""
    try:
        with get_conn() as conn:
            posts = marketing_calendar.get_scheduled_posts(
                conn,
                campaign_id=campaign_id,
                status="scheduled",
                limit=100,
            )

            for post in posts:
                marketing_calendar.mark_failed(conn, post["post_id"], "Cancelled via API")

            campaign = marketing_calendar.get_campaign_by_id(conn, campaign_id)
            if campaign:
                campaign["status"] = "cancelled"
                marketing_calendar.save_campaign(conn, campaign)

        logger.info(f"Cancelled schedule for campaign: {campaign_id}")
        return {"status": "cancelled", "campaign_id": campaign_id}

    except Exception as e:
        logger.error(f"Error cancelling schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: str) -> Dict[str, Any]:
    """Get campaign status and stats."""
    try:
        with get_conn() as conn:
            campaign = marketing_calendar.get_campaign_by_id(conn, campaign_id)
            history = campaign_log.get_campaign_history(conn, campaign_id, limit=50)
            stats = campaign_log.get_channel_stats(conn, campaign_id, days=30)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return {
            "campaign": campaign,
            "history": history,
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Analytics Agent API
FastAPI app مع lifespan كامل: DB pool + services + scheduler + event_collector.
"""
import os
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query

# Ensure the agent root is on sys.path so absolute imports work
# when launched via `uvicorn api.main:app`.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import (
    attribution_store,
    event_store,
    metric_store,
    outcome_store,
    pattern_store,
    report_store,
    signal_store,
)
from db.connection import close_pool, get_conn, init_pool
from logging_config import configure_logging, get_logger
from models import SignalOutcome
from scheduler import start_scheduler
from workflows.event_collector import start_event_collector

configure_logging()
logger = get_logger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pool + scheduler + event_collector thread. Shutdown: cleanup."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Analytics agent starting up...")

    # 1. DB connection pool
    init_pool(minconn=2, maxconn=10)

    # 2. APScheduler
    scheduler = start_scheduler()

    # 3. Event Collector في thread منفصل (blocking loop)
    collector_thread = threading.Thread(
        target=start_event_collector,
        name="event-collector",
        daemon=True,
    )
    collector_thread.start()

    logger.info("Analytics agent ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Analytics agent shutting down...")
    scheduler.shutdown(wait=False)
    close_pool()
    logger.info("Analytics agent stopped")


app = FastAPI(
    title       = "Analytics Agent API",
    description = "طبقة الاستخبارات التشغيلية — نافع",
    version     = "1.0.0",
    lifespan    = lifespan,
)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """آخر signals + آخر metrics + ملخص."""
    try:
        now = datetime.utcnow()
        since_30d = now - timedelta(days=30)

        with get_conn() as conn:
            latest_signals = signal_store.get_signals_by_type(
                conn, signal_type="all", limit=10, include_sent=True
            )
            latest_patterns = pattern_store.get_recent_patterns(conn, limit=10, days=7)
            total_sales = event_store.count_events(
                conn, event_type="NEW_SALE", since=since_30d
            )
            revenue_snapshots = metric_store.get_period_metrics(
                conn,
                period_start = since_30d,
                period_end   = now,
                granularity  = "day",
            )
            total_revenue = sum(
                float(s.get("value", 0))
                for s in revenue_snapshots
                if s.get("metric_key") == "sales_revenue"
            )

        return {
            "signals":  latest_signals,
            "patterns": latest_patterns,
            "summary":  {
                "total_sales_last_30d":   total_sales,
                "total_revenue_last_30d": total_revenue,
                "as_of":                  now.isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error in get_dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.get("/reports/weekly/{period}")
async def get_weekly_report(period: str) -> Dict[str, Any]:
    """period = 'latest' أو 'YYYY-MM-DD'."""
    try:
        with get_conn() as conn:
            if period.lower() == "latest":
                report = report_store.get_latest_report(conn)
            else:
                report = report_store.get_report(conn, report_id=f"weekly_{period}")

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_weekly_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/monthly/{year}/{month}")
async def get_monthly_report(year: int, month: int) -> Dict[str, Any]:
    try:
        with get_conn() as conn:
            report = report_store.get_report(
                conn, report_id=f"monthly_{year}_{month:02d}"
            )
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_monthly_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Signals ───────────────────────────────────────────────────────────────────

@app.get("/signals")
async def get_signals(
    type:  Optional[str] = Query(None, alias="type"),
    agent: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    limit: int           = Query(100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    try:
        since_dt = datetime.fromisoformat(since) if since else None

        with get_conn() as conn:
            signals = signal_store.get_signals_filtered(
                conn,
                signal_type  = type,
                target_agent = agent,
                since        = since_dt,
                limit        = limit,
            )
        return signals
    except Exception as e:
        logger.error(f"Error in get_signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/signals/{signal_id}/outcome")
async def record_signal_outcome(
    signal_id:    str,
    before_value: Optional[float] = None,
    after_value:  Optional[float] = None,
    action_taken: Optional[str]   = None,
    notes:        Optional[str]   = None,
) -> Dict[str, str]:
    """Signal Outcome Feedback Loop — لتحسين الإشارات مستقبلاً."""
    try:
        success_score: Optional[float] = None
        if before_value is not None and after_value is not None and before_value > 0:
            ratio = after_value / before_value
            if ratio >= 1.0:
                success_score = 1.0
            elif ratio >= 0.8:
                success_score = 0.7
            elif ratio >= 0.6:
                success_score = 0.5
            else:
                success_score = 0.3

        outcome = SignalOutcome(
            outcome_id          = f"out_{signal_id[:8]}_{int(datetime.utcnow().timestamp())}",
            signal_id           = signal_id,
            target_agent        = "",       # سيُملأ من الـ signal في DB
            action_taken        = action_taken,
            observed_metric     = None,
            before_value        = before_value,
            after_value         = after_value,
            outcome_window_days = 7,
            success_score       = success_score,
            evaluated_at        = datetime.utcnow(),
            notes               = notes,
        )

        with get_conn() as conn:
            outcome_store.save_outcome(conn, outcome)

        return {"status": "success", "outcome_id": outcome.outcome_id}
    except Exception as e:
        logger.error(f"Error recording signal outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Metrics ───────────────────────────────────────────────────────────────────

@app.get("/metrics")
async def get_metrics(
    period_start: str  = Query(...),
    period_end:   str  = Query(...),
    granularity:  str  = Query("day"),
    metric_key:   Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    try:
        start = datetime.fromisoformat(period_start)
        end   = datetime.fromisoformat(period_end)

        with get_conn() as conn:
            metrics = metric_store.get_period_metrics(
                conn,
                period_start = start,
                period_end   = end,
                granularity  = granularity,
            )

        if metric_key:
            metrics = [m for m in metrics if m.get("metric_key") == metric_key]

        return metrics
    except Exception as e:
        logger.error(f"Error in get_metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/definitions")
async def get_metric_definitions() -> List[Dict[str, Any]]:
    from ..metric_definitions import METRIC_DEFINITIONS
    return [{"key": k, **v} for k, v in METRIC_DEFINITIONS.items()]


# ── Attribution ───────────────────────────────────────────────────────────────

@app.get("/attribution/summary")
async def get_attribution_summary(days: int = Query(7, ge=1, le=90)) -> Dict[str, Any]:
    try:
        with get_conn() as conn:
            summary = attribution_store.get_attribution_summary(conn, days=days)
        return summary
    except Exception as e:
        logger.error(f"Error in get_attribution_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

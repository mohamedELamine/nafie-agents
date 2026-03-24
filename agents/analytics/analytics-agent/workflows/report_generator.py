from datetime import datetime, timedelta
from typing import Any, Dict

from ..db import metric_store
from ..db import report_store
from ..db import event_store
from ..db import pattern_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..services.resend_client import send_weekly_report

logger = get_logger("workflows.report_generator")


def generate_weekly_report(
    period_start: datetime,
    period_end: datetime,
) -> Any:
    """Generate a weekly analytics report."""
    try:
        logger.info(f"Generating weekly report: {period_start} to {period_end}")

        # Get metrics for the period
        with get_conn() as conn:
            metrics = metric_store.get_period_metrics(
                conn=conn,
                period_start=period_start,
                period_end=period_end,
                granularity="day",
            )

            sales_events = event_store.get_events(
                conn=conn,
                event_type="NEW_SALE",
                since=period_start,
                before=period_end,
                limit=1000,
            )

            patterns = pattern_store.get_recent_patterns(
                conn=conn,
                limit=10,
                days=(period_end - period_start).days,
            )

        # Aggregate metrics
        total_sales = len(sales_events)
        total_revenue = sum(e["raw_data"].get("amount_usd", 0.0) for e in sales_events)

        # Extract highlights and concerns
        highlights = []
        concerns = []

        for pattern in patterns:
            if pattern.get("is_actionable", True):
                highlights.append(f"Detected {pattern.get('pattern_type', 'pattern')}")
            else:
                concerns.append(f"Pattern: {pattern.get('pattern_type', 'pattern')}")

        # Create report object
        report = {
            "report_id": f"weekly_report_{period_start.strftime('%Y-%m-%d')}",
            "period_start": period_start,
            "period_end": period_end,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "highlights": highlights[:5],
            "concerns": concerns[:5],
            "generated_at": datetime.utcnow(),
        }

        # Save report to database
        with get_conn() as conn:
            report_store.save_report(conn, report)

        # Send report to owner
        _send_report_email(report)

        logger.info(f"Generated weekly report: {report['report_id']}")
        return report

    except Exception as e:
        logger.error(f"Error in generate_weekly_report: {e}")
        return None


def generate_monthly_report(
    month: int,
    year: int,
) -> Any:
    """Generate a monthly analytics report."""
    try:
        logger.info(f"Generating monthly report for {year}-{month:02d}")

        # Calculate date range for the month
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)

        return generate_weekly_report(first_day, last_day)

    except Exception as e:
        logger.error(f"Error in generate_monthly_report: {e}")
        return None


def _send_report_email(report: Dict[str, Any]) -> None:
    """Send report via email."""
    try:
        import os

        subject = (
            f"Weekly Analytics Report - {report['period_start'].strftime('%Y-%m-%d')}"
        )

        body = f"""
        <h1>Weekly Analytics Report</h1>
        <p><strong>Period:</strong> {report["period_start"].strftime("%Y-%m-%d")} to {report["period_end"].strftime("%Y-%m-%d")}</p>
        <h2>Summary</h2>
        <p><strong>Total Sales:</strong> {report["total_sales"]}</p>
        <p><strong>Total Revenue:</strong> ${report["total_revenue"]:,.2f}</p>
        <h2>Highlights</h2>
        <ul>
        {"".join(f"<li>{highlight}</li>" for highlight in report["highlights"])}
        </ul>
        <h2>Concerns</h2>
        <ul>
        {"".join(f"<li>{concern}</li>" for concern in report["concerns"])}
        </ul>
        <p>Generated: {report["generated_at"].isoformat()}</p>
        """

        success = send_weekly_report(
            api_key=os.getenv("RESEND_API_KEY", ""),
            owner_email=os.getenv("OWNER_EMAIL", "owner@example.com"),
            subject=subject,
            html_content=body,
        )

        if success:
            logger.info("Sent weekly report email")
        else:
            logger.error("Failed to send weekly report email")

    except Exception as e:
        logger.error(f"Error sending report email: {e}")

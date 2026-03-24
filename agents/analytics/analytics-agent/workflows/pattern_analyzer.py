from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..db import pattern_store
from ..db import signal_store
from ..db import event_store
from ..db import attribution_store
from ..db.connection import get_conn
from ..logging_config import get_logger
from ..metric_definitions import IMMEDIATE_THRESHOLDS
from ..models import Pattern, SignalType, SignalPriority

logger = get_logger("workflows.pattern_analyzer")


class OperationalPatternAnalyzer:
    """Analyze operational patterns and generate alerts."""

    def __init__(self):
        self.confidence_threshold = 0.7

    def analyze_sales_drop(self) -> Optional[Pattern]:
        """Analyze for sales drop patterns."""
        try:
            # Get sales for current week and previous week
            now = datetime.utcnow()
            with get_conn() as conn:
                current_week = event_store.get_events(
                    conn=conn,
                    event_type="NEW_SALE",
                    since=now - timedelta(days=7),
                    limit=1000,
                )
                previous_week = event_store.get_events(
                    conn=conn,
                    event_type="NEW_SALE",
                    since=now - timedelta(days=14),
                    before=now - timedelta(days=7),
                    limit=1000,
                )

            current_sales = len(current_week)
            previous_sales = len(previous_week)

            if previous_sales == 0:
                return None

            drop_percentage = (previous_sales - current_sales) / previous_sales

            if drop_percentage >= 0.50:
                return Pattern(
                    pattern_id=f"sales_drop_{int(now.timestamp())}",
                    pattern_type="SALES_DROP_7D",
                    analytics_type="OPERATIONAL",
                    confidence=0.9,
                    supporting_metrics={
                        "current_sales": current_sales,
                        "previous_sales": previous_sales,
                        "drop_percentage": drop_percentage,
                    },
                    detected_at=now,
                    is_actionable=True,
                )

            return None

        except Exception as e:
            logger.error(f"Error in analyze_sales_drop: {e}")
            return None

    def analyze_support_surge(self) -> Optional[Pattern]:
        """Analyze for support surge patterns."""
        try:
            # Get support tickets in last 24 hours
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=24)
            with get_conn() as conn:
                tickets = event_store.get_events(
                    conn=conn,
                    event_type="SUPPORT_TICKET_RESOLVED",
                    since=cutoff,
                    limit=1000,
                )

            if len(tickets) >= 10:
                return Pattern(
                    pattern_id=f"support_surge_{int(now.timestamp())}",
                    pattern_type="SUPPORT_SURGE_7D",
                    analytics_type="OPERATIONAL",
                    confidence=0.85,
                    supporting_metrics={
                        "ticket_count": len(tickets),
                        "time_window": "24 hours",
                    },
                    detected_at=datetime.utcnow(),
                    is_actionable=True,
                )

            return None

        except Exception as e:
            logger.error(f"Error in analyze_support_surge: {e}")
            return None


class BusinessPatternAnalyzer:
    """Analyze business patterns and generate insights."""

    def __init__(self):
        self.confidence_threshold = 0.6

    def analyze_best_channel(self) -> Optional[Pattern]:
        """Analyze which channel drives most sales."""
        try:
            # Get attribution data for last 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)

            with get_conn() as conn:
                records = attribution_store.get_records_by_theme(
                    conn=conn,
                    theme_slug="all",
                    limit=1000,
                )
            recent_records = [
                record
                for record in records
                if not record.get("sale_date") or record.get("sale_date") >= cutoff
            ]

            # Count sales by channel
            channel_sales: Dict[str, int] = {}
            for record in recent_records:
                attributed_to = record.get("attributed_to", "direct")
                channel_sales[attributed_to] = channel_sales.get(attributed_to, 0) + 1

            if not channel_sales:
                return None

            # Find best channel
            best_channel = max(channel_sales.items(), key=lambda x: x[1])

            if best_channel[1] > 3:  # Minimum 3 sales
                return Pattern(
                    pattern_id=f"best_channel_{int(datetime.utcnow().timestamp())}",
                    pattern_type="BEST_CHANNEL_30D",
                    analytics_type="BUSINESS",
                    confidence=0.75,
                    supporting_metrics={
                        "best_channel": best_channel[0],
                        "sales_count": best_channel[1],
                        "total_sales": sum(channel_sales.values()),
                    },
                    detected_at=datetime.utcnow(),
                    is_actionable=True,
                )

            return None

        except Exception as e:
            logger.error(f"Error in analyze_best_channel: {e}")
            return None

    def analyze_best_time(self) -> Optional[Pattern]:
        """Analyze which day/time drives most sales."""
        try:
            # Get sales data for last 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)
            with get_conn() as conn:
                events = event_store.get_events(
                    conn=conn,
                    event_type="NEW_SALE",
                    since=cutoff,
                    limit=1000,
                )

            # Count sales by day of week
            day_counts: Dict[str, int] = {}
            for event in events:
                day = event["occurred_at"].strftime("%A")
                day_counts[day] = day_counts.get(day, 0) + 1

            if day_counts:
                best_day = max(day_counts.items(), key=lambda x: x[1])

                return Pattern(
                    pattern_id=f"best_time_{int(datetime.utcnow().timestamp())}",
                    pattern_type="BEST_TIME_30D",
                    analytics_type="BUSINESS",
                    confidence=0.7,
                    supporting_metrics={
                        "best_day": best_day[0],
                        "sales_count": best_day[1],
                        "total_sales": len(events),
                    },
                    detected_at=datetime.utcnow(),
                    is_actionable=True,
                )

            return None

        except Exception as e:
            logger.error(f"Error in analyze_best_time: {e}")
            return None


def run_pattern_analysis() -> List[Pattern]:
    """Run both operational and business pattern analysis."""
    try:
        logger.info("Running pattern analysis...")

        operational_analyzer = OperationalPatternAnalyzer()
        business_analyzer = BusinessPatternAnalyzer()

        operational_patterns = [
            operational_analyzer.analyze_sales_drop(),
            operational_analyzer.analyze_support_surge(),
        ]

        business_patterns = [
            business_analyzer.analyze_best_channel(),
            business_analyzer.analyze_best_time(),
        ]

        # Filter out None values
        all_patterns = [
            p for p in operational_patterns + business_patterns if p is not None
        ]

        # Save patterns to database
        with get_conn() as conn:
            for pattern in all_patterns:
                pattern_store.save_pattern(conn, pattern.__dict__)

        logger.info(f"Generated {len(all_patterns)} patterns")
        return all_patterns

    except Exception as e:
        logger.error(f"Error in run_pattern_analysis: {e}")
        return []

import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..logging_config import configure_logging, get_logger
from .workflows.immediate_evaluator import ImmediateEvaluator
from .workflows.metrics_engine import (
    metrics_engine_batch,
    daily_aggregation,
    weekly_aggregation,
)
from .workflows.pattern_analyzer import run_pattern_analysis
from .workflows.signal_generator import generate_signals_from_patterns
from .workflows.report_generator import generate_weekly_report, generate_monthly_report
from .workflows.reconciliation import reconcile_sales_data

logger = get_logger("scheduler")


class AnalyticsScheduler:
    """Main scheduler for analytics agent tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.immediate_evaluator = ImmediateEvaluator()
        self.running = False

    def start(self) -> None:
        """Start the scheduler."""
        try:
            # Configure logging
            configure_logging(os.getenv("LOG_LEVEL", "INFO"))

            # Add jobs
            self._add_jobs()

            # Start scheduler
            self.scheduler.start()
            self.running = True

            logger.info("Analytics scheduler started")

            # Keep running
            self._run_until_interrupted()

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            sys.exit(1)

    def _add_jobs(self) -> None:
        """Add all scheduled jobs."""
        # Immediate evaluator: every 15 minutes
        self.scheduler.add_job(
            self.immediate_evaluator.run_scheduled_checks,
            "interval",
            minutes=15,
            id="immediate_evaluator",
            name="Run immediate evaluator checks",
        )

        # Metrics engine batch: every hour
        self.scheduler.add_job(
            metrics_engine_batch,
            "interval",
            hours=1,
            id="metrics_engine",
            name="Run metrics engine batch",
        )

        # Daily aggregation: daily at 01:00
        self.scheduler.add_job(
            daily_aggregation,
            "cron",
            hour=1,
            id="daily_aggregation",
            name="Run daily aggregation",
        )

        # Pattern analyzer + signal generator: daily at 03:00
        self.scheduler.add_job(
            self._run_daily_batch,
            "cron",
            hour=3,
            id="daily_batch",
            name="Run daily pattern analysis and signal generation",
        )

        # Reconcile sales data: daily at 02:00
        self.scheduler.add_job(
            reconcile_sales_data,
            "cron",
            hour=2,
            id="reconcile_sales",
            name="Reconcile sales data",
        )

        # Weekly report: Sunday at 08:00
        self.scheduler.add_job(
            self._generate_weekly_report,
            "cron",
            day_of_week="0",
            hour=8,
            id="weekly_report",
            name="Generate weekly report",
        )

        # Monthly report: 1st of month at 08:00
        self.scheduler.add_job(
            self._generate_monthly_report,
            "cron",
            day=1,
            hour=8,
            id="monthly_report",
            name="Generate monthly report",
        )

        logger.info("Added all scheduled jobs")

    async def _run_daily_batch(self) -> None:
        """Run daily batch: pattern analysis + signal generation."""
        try:
            logger.info("Running daily batch (patterns + signals)...")

            # Run pattern analysis
            patterns = run_pattern_analysis()

            # Generate signals from patterns
            signals = generate_signals_from_patterns(patterns)

            logger.info(
                f"Daily batch completed: {len(patterns)} patterns, {len(signals)} signals"
            )

        except Exception as e:
            logger.error(f"Error in daily batch: {e}")

    async def _generate_weekly_report(self) -> None:
        """Generate and send weekly report."""
        try:
            now = datetime.utcnow()
            start = now - timedelta(days=7)
            end = now

            report = generate_weekly_report(start, end)

            if report:
                logger.info(f"Generated weekly report: {report['report_id']}")
            else:
                logger.error("Failed to generate weekly report")

        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")

    async def _generate_monthly_report(self) -> None:
        """Generate and send monthly report."""
        try:
            now = datetime.utcnow()
            month = now.month
            year = now.year

            report = generate_monthly_report(month, year)

            if report:
                logger.info(f"Generated monthly report: {report['report_id']}")
            else:
                logger.error("Failed to generate monthly report")

        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")

    def _run_until_interrupted(self) -> None:
        """Keep the scheduler running until interrupted."""
        try:
            while self.running:
                await __import__("asyncio").sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
            self.running = False
            logger.info("Analytics scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")


def main() -> None:
    """Main entry point for the analytics scheduler."""
    scheduler = AnalyticsScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()

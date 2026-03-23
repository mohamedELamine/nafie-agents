import asyncio
import os
import logging
from dotenv import load_dotenv

from logging_config import configure_logging, get_logger

load_dotenv()

configure_logging()

logger = get_logger(__name__)


class Supervisor:
    def __init__(
        self,
        redis_bus,
        db_url,
        resend_api_key,
        owner_email,
        heartbeat_timeout_sec: int = 120,
        health_check_interval_sec: int = 60,
    ):
        self.redis = redis_bus
        self.db_url = db_url
        self.resend = None  # Will be initialized in main()
        self.owner_email = owner_email
        self.heartbeat_timeout = heartbeat_timeout_sec
        self.health_check_interval = health_check_interval_sec

        # Initialize components
        self.system_listener = None
        self.command_listener = None

    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("Initializing supervisor agent...")

            # Import and initialize clients
            import resend
            from workflows.health_monitor import health_monitor
            from workflows.conflict_resolver import conflict_resolver
            from db.audit_store import audit_store

            self.resend = resend.Resend(api_key=resend_api_key)

            # Initialize listeners
            self.system_listener = system_listener
            self.command_listener = command_listener

            # Set up error handlers
            self._setup_error_handlers()

            # Start listeners
            await self._start_listeners()

            # Start health monitor
            await self._start_health_monitor()

            logger.info("Supervisor agent initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing supervisor: {e}")
            raise

    async def _start_listeners(self):
        """Start listening for events"""
        try:
            await self.system_listener.start()
            await self.command_listener.start()
            logger.info("Listeners started successfully")

        except Exception as e:
            logger.error(f"Error starting listeners: {e}")
            raise

    async def _start_health_monitor(self):
        """Start health monitor scheduler"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from workflows.health_monitor import health_monitor

            scheduler = AsyncIOScheduler()

            @scheduler.scheduled_job("interval", seconds=self.health_check_interval)
            async def health_check_job():
                try:
                    await health_monitor.check_all_agents()
                except Exception as e:
                    logger.error(f"Error in health check: {e}")

            scheduler.start()
            logger.info(f"Health monitor started (check every {self.health_check_interval}s)")

        except Exception as e:
            logger.error(f"Error starting health monitor: {e}")

    def _setup_error_handlers(self):
        """Set up error handlers"""
        import sys

        async def handle_exception(loop, context):
            exception = context.get("exception")
            if exception:
                logger.error(f"Unhandled exception: {exception}")

        asyncio.get_event_loop().set_exception_handler(handle_exception)

    async def shutdown(self):
        """Graceful shutdown"""
        try:
            logger.info("Shutting down supervisor agent...")

            # Stop listeners
            await self.system_listener.stop()
            await self.command_listener.stop()

            logger.info("Supervisor agent shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point"""
    try:
        # Initialize supervisor
        supervisor = Supervisor(
            redis_bus=redis_bus,
            db_url=os.getenv(
                "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/supervisor"
            ),
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            owner_email=os.getenv("OWNER_EMAIL", "admin@yourdomain.com"),
            heartbeat_timeout_sec=int(os.getenv("HEARTBEAT_TIMEOUT_SEC", "120")),
            health_check_interval_sec=int(os.getenv("HEALTH_CHECK_INTERVAL_SEC", "60")),
        )

        await supervisor.initialize()

        # Keep running
        logger.info("Supervisor agent is running...")
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

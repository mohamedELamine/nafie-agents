import asyncio
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

from logging_config import configure_logging, get_logger
from redis_bus import RedisBus
from listeners.system_listener import SystemListener
from listeners.command_listener import CommandListener
from services.resend_client import ResendClient
from workflows.health_monitor import health_monitor
from workflows.conflict_resolver import conflict_resolver
from workflows.orchestrator import orchestrator
from db.connection import init_pool, close_pool

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
        self.resend_api_key = resend_api_key
        self.resend = None
        self.owner_email = owner_email
        self.heartbeat_timeout = heartbeat_timeout_sec
        self.health_check_interval = health_check_interval_sec
        self._listener_tasks = []

        # Initialize components
        self.system_listener = SystemListener()
        self.command_listener = CommandListener()

    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("Initializing supervisor agent...")

            self.resend = ResendClient(api_key=self.resend_api_key)
            orchestrator.resend = self.resend
            health_monitor.resend = self.resend
            conflict_resolver.resend = self.resend
            self.system_listener.resend = self.resend
            self.command_listener.resend = self.resend

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
            self._listener_tasks = [
                asyncio.create_task(self.system_listener.start(), name="supervisor-system-listener"),
                asyncio.create_task(self.command_listener.start(), name="supervisor-command-listener"),
            ]
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
            for task in self._listener_tasks:
                task.cancel()
            if self._listener_tasks:
                await asyncio.gather(*self._listener_tasks, return_exceptions=True)
            self._listener_tasks = []

            close_pool()
            logger.info("Supervisor agent shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set")

        # Initialise connection pool before any store is used
        init_pool()

        parsed_redis = urlparse(redis_url)
        redis_host = parsed_redis.hostname or "localhost"
        redis_port = parsed_redis.port or 6379

        bus = RedisBus(
            host=redis_host,
            port=redis_port,
        )

        # Initialize supervisor
        supervisor = Supervisor(
            redis_bus=bus,
            db_url=database_url,
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            owner_email=os.getenv("OWNER_EMAIL", "admin@example.com"),
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

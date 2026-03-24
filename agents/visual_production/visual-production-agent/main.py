import asyncio
from dotenv import load_dotenv

from logging_config import configure_logging, get_logger

load_dotenv()

configure_logging()

logger = get_logger(__name__)


async def main():
    """Main entry point for visual production agent"""

    logger.info("Visual Production Agent starting...")

    try:
        # Initialize services
        flux_client = None
        ideogram_client = None
        image_processor = None
        storage_client = None
        redis_bus = None
        resend_client = None
        asset_manifest_manager = None

        logger.info("Visual Production Agent is ready")
        logger.info("Waiting for THEME_APPROVED events...")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down visual production agent...")
    except Exception as e:
        logger.error(f"Error in visual production agent: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

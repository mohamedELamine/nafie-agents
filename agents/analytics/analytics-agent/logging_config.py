import logging
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict

from redis.exceptions import RedisError

if TYPE_CHECKING:
    from .services.redis_bus import RedisBus


def configure_logging(log_level: str = "INFO") -> None:
    """Configure logging with structured format."""
    log_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Apply to root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with agent=analytics prefix."""
    return logging.getLogger(f"agent.analytics.{name}")


class RedisLogHandler(logging.Handler):
    """Send log messages to Redis for centralized logging."""

    def __init__(self, redis_bus: "RedisBus"):
        super().__init__()
        self.redis_bus = redis_bus
        self.channel = "analytics:logs"

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_data: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            if record.exc_info:
                log_data["exception"] = self.format(record)

            self.redis_bus.publish(self.channel, log_data)
        except (RedisError, Exception):
            # Don't let Redis issues break the logging
            pass

"""إعداد التسجيل الموحد لوكيل المحتوى."""
import logging
import os
import sys


def configure_logging() -> None:
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    fmt   = "%(asctime)s | %(levelname)s | agent=content | %(name)s | %(message)s"
    logging.basicConfig(
        stream    = sys.stdout,
        level     = level,
        format    = fmt,
        datefmt   = "%Y-%m-%dT%H:%M:%S",
        force     = True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"content_agent.{name}")

"""
Logging configuration — Platform Agent
مُهيَّج من .env (LOG_LEVEL) بـ format موحد مع timestamp + agent_name
"""
from __future__ import annotations

import logging
import logging.config
import os
import sys


def configure_logging() -> None:
    """تهيئة logging المركزي للوكيل. يُستدعى مرة واحدة عند بدء التشغيل."""
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | agent=platform"
                    " | %(name)s | %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "json": {
                # Format بسيط يُشبه JSON لسهولة الـ parsing
                "format": (
                    '{"time":"%(asctime)s","level":"%(levelname)s",'
                    '"agent":"platform","logger":"%(name)s","msg":%(message)r}'
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            # تقليل ضجيج httpx في الـ logs
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
            # LangGraph
            "langgraph": {"level": "WARNING", "propagate": True},
            # Platform Agent — كل شيء
            "platform_agent": {"level": level, "propagate": True},
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    إنشاء logger بالاسم المحدد تحت namespace `platform_agent`.

    Usage:
        from logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("message")
    """
    if not name.startswith("platform_agent"):
        name = f"platform_agent.{name}"
    return logging.getLogger(name)

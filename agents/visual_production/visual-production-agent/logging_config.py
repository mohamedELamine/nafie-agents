import logging
from typing import Any


def configure_logging():
    """Configure logging for visual production agent"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the visual production agent"""
    return logging.getLogger(f"visual_production.{name}")

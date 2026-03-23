import logging


def configure_logging():
    """Configure logging for supervisor agent"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the supervisor agent"""
    return logging.getLogger(f"supervisor.{name}")

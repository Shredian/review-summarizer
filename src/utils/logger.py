import sys

from loguru import logger

from src.utils.config import CONFIG


def setup_logger() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=CONFIG.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )


setup_logger()

__all__ = ["logger"]

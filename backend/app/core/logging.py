"""Structured JSON logging with loguru."""

from __future__ import annotations

import sys

from loguru import logger

# Remove default handler and add structured one
logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)

# JSON log for production (file-based)
logger.add(
    "logs/indiaground.log",
    format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {name}:{function}:{line} | {message}",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
    level="INFO",
    serialize=True,
)

__all__ = ["logger"]

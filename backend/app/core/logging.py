"""Structured JSON logging with loguru.

Also configures stdlib/third-party loggers to suppress noisy model-loading
output (safetensors LOAD REPORTs, tqdm progress bars, sequential-GPU hints).
"""

from __future__ import annotations

import logging
import os
import sys
import warnings

from loguru import logger

# ── Suppress noisy third-party output ─────────────────
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("SAFETENSORS_FAST_GPU", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

for _noisy in (
    "safetensors",
    "safetensors.torch",
    "transformers",
    "transformers.modeling_utils",
    "transformers.pipelines",
    "sentence_transformers",
    "torch",
    "huggingface_hub",
    "huggingface_hub.utils",
    "filelock",
):
    logging.getLogger(_noisy).setLevel(logging.ERROR)

warnings.filterwarnings("ignore", message=".*sequentially on GPU.*")
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")
warnings.filterwarnings("ignore", message=".*not sharded.*")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
warnings.filterwarnings("ignore", category=UserWarning, module="safetensors")

# ── Loguru console handler ────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    level="INFO",
    colorize=True,
)

# ── JSON log for production (file-based) ──────────────
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

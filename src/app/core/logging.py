# File: src/alphascope/core/logging.py
"""Shared logging configuration for API and worker processes."""

import logging

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure the process-wide default logging format and level."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

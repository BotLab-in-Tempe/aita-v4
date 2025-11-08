"""Operational logging configuration for AITA infrastructure events.

This module sets up logging for operational events that should NOT be sent to
Langfuse (e.g., Docker lifecycle, DB connections, process events, security audit).
Logs are written to both stdout and a rotating file in human-readable format.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_ops_logging(
    log_level: str = "INFO",
    log_file_path: str = "logs/aita-ops.log",
    log_max_bytes: int = 10485760,  # 10MB
    log_backup_count: int = 5,
) -> logging.Logger:
    """Configure operational logging with dual output (stdout + rotating file).

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_path: Path to the log file
        log_max_bytes: Maximum size of log file before rotation
        log_backup_count: Number of backup log files to keep

    Returns:
        Configured logger instance for operational events
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create dedicated ops logger
    logger = logging.getLogger("aita.ops")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Human-readable format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


# Module-level logger instance (initialized on first import)
_logger = None


def get_logger() -> logging.Logger:
    """Get the operational logger instance.

    Returns:
        The aita.ops logger, creating it with defaults if not yet initialized
    """
    global _logger
    if _logger is None:
        _logger = setup_ops_logging()
    return _logger

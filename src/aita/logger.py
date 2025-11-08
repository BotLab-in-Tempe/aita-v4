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

    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("aita.ops")
    logger.setLevel(getattr(logging, log_level.upper()))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger


_logger = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = setup_ops_logging()
    return _logger

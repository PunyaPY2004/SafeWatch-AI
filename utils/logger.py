"""
utils/logger.py
================
Centralized logging setup for all SafeWatch AI modules.
"""

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """Create and return a named logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger   # Already configured

    logger.setLevel(level)

    fmt = logging.Formatter(
        fmt     = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    log_file = os.path.join(LOG_DIR, f"safewatch_{datetime.now().strftime('%Y%m%d')}.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

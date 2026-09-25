"""Structured logging for the File Organizer Bot.

Provides consistent logging across all modules with both file and
console output.  Call ``setup_logging()`` once at application start;
then use ``get_logger(name)`` in each module.
"""

import logging
import os


_LOG_DIR = os.path.join(os.path.expanduser("~"), ".file_organizer")
_LOG_FILE = os.path.join(_LOG_DIR, "organizer.log")
_initialised = False


def setup_logging(
    level: int = logging.INFO,
    log_file: str = None,
) -> logging.Logger:
    """Configure and return the root application logger.

    Safe to call multiple times — subsequent calls return the existing
    logger without adding duplicate handlers.

    Args:
        level: Logging level (default ``INFO``).
        log_file: Custom log-file path.
                  Defaults to ``~/.file_organizer/organizer.log``.

    Returns:
        The configured ``file_organizer`` logger.
    """
    global _initialised

    logger = logging.getLogger("file_organizer")

    if _initialised:
        return logger

    log_path = log_file or _LOG_FILE
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)

    logger.setLevel(level)

    # ── File handler – detailed ──────────────────────────────────────────
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # ── Console handler – warnings and above ─────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    _initialised = True
    logger.info("Logging initialised — %s", log_path)
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Return a child logger, initialising the root logger if necessary."""
    if not _initialised:
        setup_logging()

    root = logging.getLogger("file_organizer")
    return root.getChild(name) if name else root

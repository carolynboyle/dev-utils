"""
nmkit.logger - Logging configuration for nmkit.

Provides a single setup_logger() function that configures the nmkit
logger with a rotating file handler and a stderr console handler.

Log files are written to ~/.local/share/nmkit/nmkit.log by default.
Override by passing log_dir explicitly (useful for testing).

Usage:
    from nmkit.logger import setup_logger

    setup_logger()
    log = logging.getLogger("nmkit")
    log.info("Ready.")

The logger is named 'nmkit' throughout. Other nmkit modules use:
    import logging
    log = logging.getLogger("nmkit")

setup_logger() should be called once, at entry point (__main__.py).
It should NOT be called at module import time.
"""

import logging
import logging.handlers
from pathlib import Path


# Default log directory — XDG-compliant user data location.
_DEFAULT_LOG_DIR = Path.home() / ".local" / "share" / "nmkit"

# Log file size and backup count for rotation.
# 1MB per file, keep 3 backups = max 4MB of logs retained.
_MAX_BYTES    = 1_000_000
_BACKUP_COUNT = 3


def setup_logger(log_dir: Path | None = None) -> None:
    """
    Configure the nmkit logger.

    Sets up two handlers:
      - RotatingFileHandler: writes INFO+ to <log_dir>/nmkit.log
      - StreamHandler:       writes WARNING+ to stderr

    DEBUG messages go to the file only. The console stays quiet unless
    something goes wrong.

    Args:
        log_dir: Override log directory. Defaults to
                 ~/.local/share/nmkit/. Useful for testing.

    Returns:
        None. Callers retrieve the logger via logging.getLogger("nmkit").
    """
    if log_dir is None:
        log_dir = _DEFAULT_LOG_DIR

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "nmkit.log"

    logger = logging.getLogger("nmkit")
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if setup_logger() is called more
    # than once (e.g. in tests).
    if logger.handlers:
        return

    # -- File handler (rotating) ----------------------------------------------
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # -- Console handler (stderr) ---------------------------------------------
    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)

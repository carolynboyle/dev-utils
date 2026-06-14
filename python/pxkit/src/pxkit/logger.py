"""
pxkit.logger - Logging configuration for pxkit.

Provides a single setup_logger() function that configures the pxkit
logger with a rotating file handler and a stderr console handler.

Log files are written to ~/.local/share/pxkit/pxkit.log by default.
Override by passing log_dir explicitly (useful for testing).

Verbosity levels:
    verbose  DEBUG to file and console — full .vv content, API calls,
             keyring lookups, remote-viewer command lines.
    normal   INFO to file, WARNING to console. Default.
    quiet    WARNING to file only, nothing to console. For autostart.

Usage:
    from pxkit.logger import setup_logger

    setup_logger()                    # normal
    setup_logger(verbosity="verbose") # debug everything
    setup_logger(verbosity="quiet")   # autostart

The logger is named 'pxkit' throughout. Other pxkit modules use:
    import logging
    log = logging.getLogger("pxkit")

setup_logger() should be called once, at entry point (__main__.py).
It should NOT be called at module import time.
"""

import logging
import logging.handlers
from pathlib import Path


# Default log directory — XDG-compliant user data location.
_DEFAULT_LOG_DIR = Path.home() / ".local" / "share" / "pxkit"

# Log file size and backup count for rotation.
# 1MB per file, keep 3 backups = max 4MB of logs retained.
_MAX_BYTES    = 1_000_000
_BACKUP_COUNT = 3

# Valid verbosity levels mapped to (file_level, console_level).
# console_level of None means no console output.
_LEVELS = {
    "verbose": (logging.DEBUG, logging.DEBUG),
    "normal":  (logging.INFO,  logging.WARNING),
    "quiet":   (logging.WARNING, None),
}


def setup_logger(
    verbosity: str = "normal",
    log_dir: Path | None = None,
) -> None:
    """
    Configure the pxkit logger.

    Sets up two handlers:
      - RotatingFileHandler: writes to <log_dir>/pxkit.log
      - StreamHandler:       writes to stderr (omitted in quiet mode)

    Args:
        verbosity: One of 'verbose', 'normal', 'quiet'. Defaults to
                   'normal'. Invalid values fall back to 'normal'.
        log_dir:   Override log directory. Defaults to
                   ~/.local/share/pxkit/. Useful for testing.

    Returns:
        None. Callers retrieve the logger via logging.getLogger("pxkit").
    """
    if log_dir is None:
        log_dir = _DEFAULT_LOG_DIR

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pxkit.log"

    if verbosity not in _LEVELS:
        verbosity = "normal"

    file_level, console_level = _LEVELS[verbosity]

    logger = logging.getLogger("pxkit")
    logger.setLevel(logging.DEBUG)  # Handler levels do the filtering.

    # Avoid adding duplicate handlers if setup_logger() is called more
    # than once (e.g. in tests).
    if logger.handlers:
        return

    fmt_file    = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_console = logging.Formatter("[%(levelname)s] %(message)s")

    # -- File handler (rotating) ----------------------------------------------
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(fmt_file)
    logger.addHandler(file_handler)

    # -- Console handler (stderr) — omitted in quiet mode --------------------
    if console_level is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(fmt_console)
        logger.addHandler(console_handler)

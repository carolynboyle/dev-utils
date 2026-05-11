# logger.py

**Path:** python/setupkit/src/setupkit/logger.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
setupkit.logger - Logging configuration for setupkit.

Provides a single setup_logger() function that configures the setupkit
logger with a rotating file handler and a stderr console handler.

Log location is read from ConfigManager (which reads setupkit.yaml and
the user's dev-utils config.yaml). This keeps log paths consistent with
the rest of the setupkit configuration rather than hardcoding them.

Usage:
    from setupkit.logger import setup_logger

    setup_logger()
    log = logging.getLogger("setupkit")
    log.info("Ready.")

The logger is named 'setupkit' throughout. Other setupkit modules use:
    import logging
    log = logging.getLogger("setupkit")

setup_logger() should be called once, at CLI entry point (main()).
It should NOT be called at module import time.
"""

import logging
import logging.handlers
from pathlib import Path

from setupkit.config import ConfigManager


# Log file size and backup count for rotation.
# 1MB per file, keep 3 backups = max 4MB of logs retained.
_MAX_BYTES    = 1_000_000
_BACKUP_COUNT = 3


def setup_logger(log_dir: Path | None = None) -> None:
    """
    Configure the setupkit logger.

    Sets up two handlers:
      - RotatingFileHandler: writes INFO+ to <log_dir>/setupkit.log
      - StreamHandler:       writes WARNING+ to stderr (visible on problems)

    DEBUG messages go to the file only. The console stays quiet unless
    something goes wrong.

    Args:
        log_dir: Override log directory. Defaults to ConfigManager().log_dir.
                 Useful for testing.

    Returns:
        None. Callers retrieve the logger via logging.getLogger("setupkit").
    """
    if log_dir is None:
        config  = ConfigManager()
        log_dir = config.log_dir

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "setupkit.log"

    logger = logging.getLogger("setupkit")
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if setup_logger() is called more
    # than once (e.g. in tests).
    if logger.handlers:
        return

    # -- File handler (rotating) -------------------------------------------
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

    # -- Console handler (stderr) ------------------------------------------
    sh = logging.StreamHandler()   # defaults to sys.stderr
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)
    
```

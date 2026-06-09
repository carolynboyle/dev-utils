"""
logger.py — Run logger for pack-kit.

Writes a plain-text run log to ~/.config/dev-utils/packkit/packkit.log
and buffers entries for printing to stdout on completion or failure.
The log is also the run report — a log failure is always fatal.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from packkit.exceptions import LogError

LOG_DIR = Path.home() / '.config' / 'dev-utils' / 'packkit'
LOG_FILE = LOG_DIR / 'packkit.log'


class RunLogger:
    """
    Buffers log entries for a single pack run and writes them on close.

    Args:
        pack_name: Name of the pack being run (used in log header).
    """

    def __init__(self, pack_name: str) -> None:
        self._pack_name = pack_name
        self._started = datetime.now()
        self._entries: list[str] = []

    def log(self, message: str) -> None:
        """
        Buffer a log entry.

        Args:
            message: Log message.
        """
        self._entries.append(message)

    def close(self, success: bool) -> None:
        """
        Write buffered entries to the log file and print to stdout.

        Args:
            success: Whether the run completed successfully.

        Raises:
            LogError: If the log file cannot be written.
        """
        status = 'SUCCESS' if success else 'FAILED'
        lines = [
            f"=== {self._started.strftime('%Y-%m-%d %H:%M:%S')} ===",
            f"Pack:   {self._pack_name}",
            f"Status: {status}",
            '',
        ] + self._entries + ['===', '']

        text = '\n'.join(lines)
        print(text)
        self._write(text)

    def _write(self, text: str) -> None:
        """
        Write text to the log file, creating directories if needed.

        Args:
            text: Full log text to append.

        Raises:
            LogError: If the log cannot be written.
        """
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LogError(f"Could not create log directory {LOG_DIR}: {exc}") from exc

        try:
            with LOG_FILE.open('a', encoding='utf-8') as f:
                f.write(text)
        except OSError as exc:
            raise LogError(f"Could not write to log file {LOG_FILE}: {exc}") from exc

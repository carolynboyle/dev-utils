"""
collector.py — File, directory, and command collection for pack-kit.

Copies files and directories into the staging area and runs commands,
capturing their output as text files. Any failure aborts the run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from packkit.config import CommandConfig
from packkit.exceptions import (
    CommandError,
    DirectoryCollectionError,
    FileCollectionError,
)


class Collector:
    """
    Collects files, directories, and command output into a staging directory.

    Args:
        staging_dir: Root of the staging directory tree.
    """

    COMMANDS_DIR = 'commands'

    def __init__(self, staging_dir: Path) -> None:
        self._staging = staging_dir

    def collect_file(self, source: Path) -> None:
        """
        Copy a single file into the staging area, preserving its absolute path.

        Args:
            source: Absolute path to the source file.

        Raises:
            FileCollectionError: If the file does not exist or cannot be copied.
        """
        if not source.exists():
            raise FileCollectionError(f"File not found: {source}")
        if not source.is_file():
            raise FileCollectionError(f"Path is not a file: {source}")

        dest = self._staging / source.relative_to('/')
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        except OSError as exc:
            raise FileCollectionError(f"Could not copy {source}: {exc}") from exc

    def collect_directory(self, source: Path) -> None:
        """
        Recursively copy a directory into the staging area, preserving its path.

        Args:
            source: Absolute path to the source directory.

        Raises:
            DirectoryCollectionError: If the directory does not exist or cannot be copied.
        """
        if not source.exists():
            raise DirectoryCollectionError(f"Directory not found: {source}")
        if not source.is_dir():
            raise DirectoryCollectionError(f"Path is not a directory: {source}")

        dest = self._staging / source.relative_to('/')
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        except OSError as exc:
            raise DirectoryCollectionError(
                f"Could not copy directory {source}: {exc}"
            ) from exc

    def collect_command(self, command: CommandConfig) -> None:
        """
        Run a shell command and write its output to commands/<label>.txt.

        Args:
            command: CommandConfig with label and run string.

        Raises:
            CommandError: If the command fails or cannot be executed.
        """
        commands_dir = self._staging / self.COMMANDS_DIR
        try:
            commands_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CommandError(
                f"Could not create commands directory: {exc}"
            ) from exc

        try:
            result = subprocess.run(
                command.run,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError(
                f"Command '{command.label}' timed out after 60 seconds"
            ) from exc
        except OSError as exc:
            raise CommandError(
                f"Could not execute command '{command.label}': {exc}"
            ) from exc

        if result.returncode != 0:
            raise CommandError(
                f"Command '{command.label}' failed (exit {result.returncode}):\n"
                f"{result.stderr.strip()}"
            )

        output_file = commands_dir / f"{command.label}.txt"
        try:
            output_file.write_text(result.stdout, encoding='utf-8')
        except OSError as exc:
            raise CommandError(
                f"Could not write output for command '{command.label}': {exc}"
            ) from exc

"""
packer.py — Staging directory and tarball creation for pack-kit.

Orchestrates the full pack run: creates the staging directory, drives
the Collector, then tarballs the result into the destination directory.
"""

from __future__ import annotations

import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from packkit.collector import Collector
from packkit.config import PackConfig
from packkit.exceptions import ArchiveError, StagingError
from packkit.logger import RunLogger


class Packer:
    """
    Orchestrates collection and archiving for a pack run.

    Args:
        config: Validated PackConfig.
        logger: RunLogger instance for this run.
    """

    def __init__(self, config: PackConfig, logger: RunLogger) -> None:
        self._config = config
        self._logger = logger

    def run(self) -> Path:
        """
        Execute the full pack run.

        Creates a staging directory, collects all files/directories/commands,
        then tarballs the result into config.destination.

        Returns:
            Path to the created tarball.

        Raises:
            StagingError: If the staging directory cannot be created.
            FileCollectionError: If a file cannot be collected.
            DirectoryCollectionError: If a directory cannot be collected.
            CommandError: If a command fails.
            ArchiveError: If the tarball cannot be created.
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        archive_name = f"{self._config.pack_name}-{timestamp}"

        self._logger.log(f"Starting pack run: {archive_name}")

        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / archive_name
            try:
                staging.mkdir()
            except OSError as exc:
                raise StagingError(f"Could not create staging directory: {exc}") from exc

            collector = Collector(staging)

            for file_path in self._config.files:
                self._logger.log(f"Collecting file: {file_path}")
                collector.collect_file(file_path)

            for dir_path in self._config.directories:
                self._logger.log(f"Collecting directory: {dir_path}")
                collector.collect_directory(dir_path)

            for command in self._config.commands:
                self._logger.log(f"Running command: {command.label}")
                collector.collect_command(command)

            tarball = self._create_tarball(staging, archive_name)

        self._logger.log(f"Archive created: {tarball}")
        return tarball

    def _create_tarball(self, staging: Path, archive_name: str) -> Path:
        """
        Create a gzipped tarball of the staging directory.

        Args:
            staging:      Path to the staging directory.
            archive_name: Base name for the tarball (no extension).

        Returns:
            Path to the created tarball.

        Raises:
            ArchiveError: If the tarball cannot be created.
        """
        dest = self._config.destination
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArchiveError(f"Could not create destination directory {dest}: {exc}") from exc

        tarball_path = dest / f"{archive_name}.tar.gz"

        try:
            with tarfile.open(tarball_path, 'w:gz') as tar:
                tar.add(staging, arcname=archive_name)
        except OSError as exc:
            raise ArchiveError(f"Could not create tarball {tarball_path}: {exc}") from exc

        return tarball_path

"""
test_packer.py — Tests for the Packer class.

Covers:
    - Happy path: tarball created at destination
    - Tarball is a valid gzip archive
    - Archive contains expected paths
    - Tarball filename includes pack_name and timestamp
    - PackerError propagates when collector fails
    - Destination directory created if it does not exist
"""

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from packkit.config import CommandConfig, PackConfig
from packkit.exceptions import FileCollectionError
from packkit.logger import RunLogger
from packkit.packer import Packer


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def make_packer(config: PackConfig) -> Packer:
    """Create a Packer with a real RunLogger."""
    logger = RunLogger(config.pack_name)
    return Packer(config, logger)


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------

class TestPackerHappyPath:
    """Packer creates a valid tarball."""

    def test_tarball_created(self, minimal_config):
        """run() creates a .tar.gz file at the destination."""
        packer = make_packer(minimal_config)
        tarball = packer.run()
        assert tarball.exists()
        assert tarball.suffix == '.gz'
        assert '.tar' in tarball.name

    def test_tarball_is_valid_gzip(self, minimal_config):
        """The created file is a valid gzip tarball."""
        packer = make_packer(minimal_config)
        tarball = packer.run()
        assert tarfile.is_tarfile(tarball)

    def test_tarball_name_contains_pack_name(self, minimal_config):
        """Tarball filename starts with the pack_name."""
        packer = make_packer(minimal_config)
        tarball = packer.run()
        assert tarball.name.startswith('test-server-')

    def test_tarball_in_destination(self, minimal_config):
        """Tarball is created inside the destination directory."""
        packer = make_packer(minimal_config)
        tarball = packer.run()
        assert tarball.parent == minimal_config.destination

    def test_destination_created_if_missing(self, tmp_path):
        """Packer creates the destination directory if it does not exist."""
        config = PackConfig(
            pack_name='test-server',
            destination=tmp_path / 'new' / 'nested' / 'dir',
            files=[],
            directories=[],
            commands=[],
            ship=None,
        )
        packer = make_packer(config)
        tarball = packer.run()
        assert tarball.exists()

    def test_tarball_contains_archive_root(self, minimal_config):
        """Archive contains a root directory matching the pack name."""
        packer = make_packer(minimal_config)
        tarball = packer.run()
        with tarfile.open(tarball, 'r:gz') as tar:
            names = tar.getnames()
        assert any(n.startswith('test-server-') for n in names)


# -----------------------------------------------------------------------------
# Files and commands in archive
# -----------------------------------------------------------------------------

class TestPackerArchiveContents:
    """Archive contains collected files and command output."""

    def test_collected_file_in_archive(self, tmp_path, sample_files):
        """A collected file appears in the archive."""
        config = PackConfig(
            pack_name='test-server',
            destination=tmp_path / 'output',
            files=[sample_files['file1']],
            directories=[],
            commands=[],
            ship=None,
        )
        packer = make_packer(config)
        tarball = packer.run()
        with tarfile.open(tarball, 'r:gz') as tar:
            names = tar.getnames()
        assert any('hostname' in n for n in names)

    def test_command_output_in_archive(self, tmp_path):
        """Command output file appears in the archive."""
        config = PackConfig(
            pack_name='test-server',
            destination=tmp_path / 'output',
            files=[],
            directories=[],
            commands=[CommandConfig(label='test-cmd', run='echo hello')],
            ship=None,
        )
        packer = make_packer(config)
        tarball = packer.run()
        with tarfile.open(tarball, 'r:gz') as tar:
            names = tar.getnames()
        assert any('test-cmd.txt' in n for n in names)


# -----------------------------------------------------------------------------
# Error propagation
# -----------------------------------------------------------------------------

class TestPackerErrorPropagation:
    """Packer propagates collector errors correctly."""

    def test_missing_file_raises(self, tmp_path):
        """FileCollectionError raised when a configured file does not exist."""
        config = PackConfig(
            pack_name='test-server',
            destination=tmp_path / 'output',
            files=[Path('/this/file/does/not/exist.txt')],
            directories=[],
            commands=[],
            ship=None,
        )
        packer = make_packer(config)
        with pytest.raises(FileCollectionError):
            packer.run()

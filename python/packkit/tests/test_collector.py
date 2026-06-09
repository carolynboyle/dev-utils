"""
test_collector.py — Tests for the Collector class.

Covers:
    - collect_file: happy path — file copied, path preserved
    - collect_file: FileCollectionError on missing file
    - collect_file: FileCollectionError when path is a directory
    - collect_directory: happy path — directory copied recursively
    - collect_directory: DirectoryCollectionError on missing directory
    - collect_directory: DirectoryCollectionError when path is a file
    - collect_command: happy path — output written to commands/<label>.txt
    - collect_command: CommandError on non-zero exit
    - collect_command: CommandError on command not found
    - collect_command: path structure preserved under staging root
"""

from pathlib import Path

import pytest

from packkit.collector import Collector
from packkit.config import CommandConfig
from packkit.exceptions import (
    CommandError,
    DirectoryCollectionError,
    FileCollectionError,
)


# -----------------------------------------------------------------------------
# collect_file
# -----------------------------------------------------------------------------

class TestCollectFile:
    """Collector.collect_file copies files into the staging area."""

    def test_file_copied(self, staging_dir, sample_files):
        """File is copied into the staging directory."""
        collector = Collector(staging_dir)
        collector.collect_file(sample_files['file1'])
        dest = staging_dir / sample_files['file1'].relative_to('/')
        assert dest.exists()
        assert dest.is_file()

    def test_file_contents_preserved(self, staging_dir, sample_files):
        """File contents are preserved after copying."""
        collector = Collector(staging_dir)
        collector.collect_file(sample_files['file1'])
        dest = staging_dir / sample_files['file1'].relative_to('/')
        assert dest.read_text(encoding='utf-8') == sample_files['file1'].read_text(encoding='utf-8')

    def test_path_structure_preserved(self, staging_dir, sample_files):
        """File is placed under its original absolute path structure."""
        collector = Collector(staging_dir)
        collector.collect_file(sample_files['file1'])
        expected = staging_dir / sample_files['file1'].relative_to('/')
        assert expected.exists()

    def test_missing_file_raises(self, staging_dir, tmp_path):
        """FileCollectionError raised for a non-existent file."""
        collector = Collector(staging_dir)
        with pytest.raises(FileCollectionError):
            collector.collect_file(tmp_path / 'does_not_exist.txt')

    def test_directory_as_file_raises(self, staging_dir, sample_files):
        """FileCollectionError raised when path is a directory."""
        collector = Collector(staging_dir)
        with pytest.raises(FileCollectionError):
            collector.collect_file(sample_files['subdir'])


# -----------------------------------------------------------------------------
# collect_directory
# -----------------------------------------------------------------------------

class TestCollectDirectory:
    """Collector.collect_directory copies directories recursively."""

    def test_directory_copied(self, staging_dir, sample_files):
        """Directory is copied into the staging area."""
        collector = Collector(staging_dir)
        collector.collect_directory(sample_files['subdir'])
        dest = staging_dir / sample_files['subdir'].relative_to('/')
        assert dest.exists()
        assert dest.is_dir()

    def test_subdirectory_contents_copied(self, staging_dir, sample_files):
        """Files inside the directory are copied."""
        collector = Collector(staging_dir)
        collector.collect_directory(sample_files['subdir'])
        dest_file = staging_dir / sample_files['subfile'].relative_to('/')
        assert dest_file.exists()

    def test_path_structure_preserved(self, staging_dir, sample_files):
        """Directory is placed under its original absolute path structure."""
        collector = Collector(staging_dir)
        collector.collect_directory(sample_files['subdir'])
        expected = staging_dir / sample_files['subdir'].relative_to('/')
        assert expected.is_dir()

    def test_missing_directory_raises(self, staging_dir, tmp_path):
        """DirectoryCollectionError raised for a non-existent directory."""
        collector = Collector(staging_dir)
        with pytest.raises(DirectoryCollectionError):
            collector.collect_directory(tmp_path / 'does_not_exist')

    def test_file_as_directory_raises(self, staging_dir, sample_files):
        """DirectoryCollectionError raised when path is a file."""
        collector = Collector(staging_dir)
        with pytest.raises(DirectoryCollectionError):
            collector.collect_directory(sample_files['file1'])


# -----------------------------------------------------------------------------
# collect_command
# -----------------------------------------------------------------------------

class TestCollectCommand:
    """Collector.collect_command runs commands and saves output."""

    def test_output_file_created(self, staging_dir):
        """Output file is created at commands/<label>.txt."""
        collector = Collector(staging_dir)
        cmd = CommandConfig(label='test-cmd', run='echo hello')
        collector.collect_command(cmd)
        output = staging_dir / 'commands' / 'test-cmd.txt'
        assert output.exists()

    def test_output_contents(self, staging_dir):
        """Command output is written to the file."""
        collector = Collector(staging_dir)
        cmd = CommandConfig(label='test-cmd', run='echo hello')
        collector.collect_command(cmd)
        output = staging_dir / 'commands' / 'test-cmd.txt'
        assert 'hello' in output.read_text(encoding='utf-8')

    def test_nonzero_exit_raises(self, staging_dir):
        """CommandError raised when command exits non-zero."""
        collector = Collector(staging_dir)
        cmd = CommandConfig(label='fail-cmd', run='exit 1')
        with pytest.raises(CommandError):
            collector.collect_command(cmd)

    def test_nonexistent_command_raises(self, staging_dir):
        """CommandError raised when command is not found."""
        collector = Collector(staging_dir)
        cmd = CommandConfig(label='bad-cmd', run='this_command_does_not_exist_xyz')
        with pytest.raises(CommandError):
            collector.collect_command(cmd)

    def test_multiple_commands_separate_files(self, staging_dir):
        """Multiple commands produce separate output files."""
        collector = Collector(staging_dir)
        collector.collect_command(CommandConfig(label='cmd-a', run='echo a'))
        collector.collect_command(CommandConfig(label='cmd-b', run='echo b'))
        assert (staging_dir / 'commands' / 'cmd-a.txt').exists()
        assert (staging_dir / 'commands' / 'cmd-b.txt').exists()

# pack-kit test suite
# All files go under python/packkit/tests/

---

## conftest.py

```python
"""
conftest.py — Shared pytest fixtures for packkit tests.

Provides reusable config objects, temp directory structures, and
mock helpers used across the test suite.
"""

from pathlib import Path

import pytest
import yaml

from packkit.config import CommandConfig, PackConfig, ShipConfig


# -----------------------------------------------------------------------------
# Minimal valid config dict (as parsed YAML would produce)
# -----------------------------------------------------------------------------

MINIMAL_CONFIG_DICT = {
    'pack_name': 'test-server',
    'destination': '/tmp',
    'files': [],
    'directories': [],
    'commands': [],
}


FULL_CONFIG_DICT = {
    'pack_name': 'test-server',
    'destination': '/tmp',
    'files': ['/etc/hostname', '/etc/hosts'],
    'directories': ['/etc/ssh'],
    'commands': [
        {'label': 'os-release', 'run': 'cat /etc/os-release'},
        {'label': 'kernel', 'run': 'uname -r'},
    ],
    'ship': {
        'enabled': True,
        'user': 'carolyn',
        'host': '192.168.10.2',
        'path': '/srv/backups',
        'key': '~/.ssh/id_ed25519',
    },
}


# -----------------------------------------------------------------------------
# YAML file fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def minimal_yaml(tmp_path) -> Path:
    """Write a minimal valid packkit.yaml to a temp directory."""
    config_file = tmp_path / 'packkit.yaml'
    config_file.write_text(yaml.dump(MINIMAL_CONFIG_DICT), encoding='utf-8')
    return config_file


@pytest.fixture
def full_yaml(tmp_path) -> Path:
    """Write a full valid packkit.yaml to a temp directory."""
    config_file = tmp_path / 'packkit.yaml'
    config_file.write_text(yaml.dump(FULL_CONFIG_DICT), encoding='utf-8')
    return config_file


# -----------------------------------------------------------------------------
# PackConfig fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def minimal_config(tmp_path) -> PackConfig:
    """A minimal PackConfig with no files, directories, commands, or ship."""
    return PackConfig(
        pack_name='test-server',
        destination=tmp_path / 'output',
        files=[],
        directories=[],
        commands=[],
        ship=None,
    )


@pytest.fixture
def full_config(tmp_path) -> PackConfig:
    """A PackConfig with files, directories, commands, and ship enabled."""
    return PackConfig(
        pack_name='test-server',
        destination=tmp_path / 'output',
        files=[tmp_path / 'etc' / 'hostname'],
        directories=[tmp_path / 'etc' / 'ssh'],
        commands=[
            CommandConfig(label='os-release', run='echo "AlmaLinux"'),
            CommandConfig(label='kernel', run='echo "5.14.0"'),
        ],
        ship=ShipConfig(
            enabled=True,
            user='carolyn',
            host='192.168.10.2',
            path='/srv/backups',
            key=None,
        ),
    )


# -----------------------------------------------------------------------------
# Filesystem fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_files(tmp_path) -> dict:
    """
    Create a small set of real files and directories under tmp_path.

    Returns a dict with keys:
        file1, file2  — individual files
        subdir        — a directory containing subfile
        subfile       — a file inside subdir
    """
    etc = tmp_path / 'etc'
    etc.mkdir()

    hostname = etc / 'hostname'
    hostname.write_text('test-server\n', encoding='utf-8')

    hosts = etc / 'hosts'
    hosts.write_text('127.0.0.1 localhost\n', encoding='utf-8')

    ssh_dir = etc / 'ssh'
    ssh_dir.mkdir()
    sshd_config = ssh_dir / 'sshd_config'
    sshd_config.write_text('Port 22\nPubkeyAuthentication yes\n', encoding='utf-8')

    return {
        'file1': hostname,
        'file2': hosts,
        'subdir': ssh_dir,
        'subfile': sshd_config,
    }


@pytest.fixture
def staging_dir(tmp_path) -> Path:
    """An empty staging directory."""
    staging = tmp_path / 'staging' / 'test-server-20260101-120000'
    staging.mkdir(parents=True)
    return staging
```

---

## test_exceptions.py

```python
"""
test_exceptions.py — Tests for the packkit exception hierarchy.

Covers:
    - All exceptions are subclasses of PackkitError
    - Each subsystem hierarchy is correct
    - Exceptions can be caught at every level
    - Exception messages are preserved
"""

import pytest

from packkit.exceptions import (
    ArchiveError,
    CollectorError,
    CommandError,
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    DirectoryCollectionError,
    FileCollectionError,
    LogError,
    PackerError,
    PackkitError,
    ScpError,
    ShipperError,
    StagingError,
)


# -----------------------------------------------------------------------------
# Hierarchy — inheritance checks
# -----------------------------------------------------------------------------

class TestHierarchy:
    """All exceptions inherit correctly from their base classes."""

    # --- Config --------------------------------------------------------------

    def test_config_error_is_packkit_error(self):
        assert issubclass(ConfigError, PackkitError)

    def test_config_not_found_is_config_error(self):
        assert issubclass(ConfigNotFoundError, ConfigError)

    def test_config_not_found_is_packkit_error(self):
        assert issubclass(ConfigNotFoundError, PackkitError)

    def test_config_parse_error_is_config_error(self):
        assert issubclass(ConfigParseError, ConfigError)

    def test_config_validation_error_is_config_error(self):
        assert issubclass(ConfigValidationError, ConfigError)

    # --- Collector -----------------------------------------------------------

    def test_collector_error_is_packkit_error(self):
        assert issubclass(CollectorError, PackkitError)

    def test_file_collection_error_is_collector_error(self):
        assert issubclass(FileCollectionError, CollectorError)

    def test_file_collection_error_is_packkit_error(self):
        assert issubclass(FileCollectionError, PackkitError)

    def test_directory_collection_error_is_collector_error(self):
        assert issubclass(DirectoryCollectionError, CollectorError)

    def test_command_error_is_collector_error(self):
        assert issubclass(CommandError, CollectorError)

    # --- Packer --------------------------------------------------------------

    def test_packer_error_is_packkit_error(self):
        assert issubclass(PackerError, PackkitError)

    def test_staging_error_is_packer_error(self):
        assert issubclass(StagingError, PackerError)

    def test_archive_error_is_packer_error(self):
        assert issubclass(ArchiveError, PackerError)

    # --- Shipper -------------------------------------------------------------

    def test_shipper_error_is_packkit_error(self):
        assert issubclass(ShipperError, PackkitError)

    def test_scp_error_is_shipper_error(self):
        assert issubclass(ScpError, ShipperError)

    def test_scp_error_is_packkit_error(self):
        assert issubclass(ScpError, PackkitError)

    # --- Log -----------------------------------------------------------------

    def test_log_error_is_packkit_error(self):
        assert issubclass(LogError, PackkitError)


# -----------------------------------------------------------------------------
# Catch at base class
# -----------------------------------------------------------------------------

class TestCatchAtBaseClass:
    """Specific exceptions can be caught at every level of the hierarchy."""

    def test_config_not_found_caught_as_config_error(self):
        with pytest.raises(ConfigError):
            raise ConfigNotFoundError("not found")

    def test_config_not_found_caught_as_packkit_error(self):
        with pytest.raises(PackkitError):
            raise ConfigNotFoundError("not found")

    def test_file_collection_error_caught_as_collector_error(self):
        with pytest.raises(CollectorError):
            raise FileCollectionError("missing file")

    def test_command_error_caught_as_collector_error(self):
        with pytest.raises(CollectorError):
            raise CommandError("command failed")

    def test_staging_error_caught_as_packer_error(self):
        with pytest.raises(PackerError):
            raise StagingError("staging failed")

    def test_archive_error_caught_as_packer_error(self):
        with pytest.raises(PackerError):
            raise ArchiveError("tarball failed")

    def test_scp_error_caught_as_shipper_error(self):
        with pytest.raises(ShipperError):
            raise ScpError("scp failed")

    def test_log_error_caught_as_packkit_error(self):
        with pytest.raises(PackkitError):
            raise LogError("log failed")


# -----------------------------------------------------------------------------
# Message preservation
# -----------------------------------------------------------------------------

class TestMessagePreservation:
    """Exception messages are accessible after raise."""

    def test_config_not_found_message(self):
        with pytest.raises(ConfigNotFoundError) as exc_info:
            raise ConfigNotFoundError("packkit.yaml not found in /tmp")
        assert "packkit.yaml not found in /tmp" in str(exc_info.value)

    def test_file_collection_error_message(self):
        with pytest.raises(FileCollectionError) as exc_info:
            raise FileCollectionError("File not found: /etc/missing")
        assert "/etc/missing" in str(exc_info.value)

    def test_command_error_message(self):
        with pytest.raises(CommandError) as exc_info:
            raise CommandError("Command 'rpm -qa' failed (exit 127)")
        assert "rpm -qa" in str(exc_info.value)

    def test_scp_error_message(self):
        with pytest.raises(ScpError) as exc_info:
            raise ScpError("scp failed (exit 1): Connection refused")
        assert "Connection refused" in str(exc_info.value)
```

---

## test_config.py

```python
"""
test_config.py — Tests for the packkit config loader and validator.

Covers:
    - Happy path: minimal config loads correctly
    - Happy path: full config with ship section loads correctly
    - Default config file lookup (packkit.yaml in cwd)
    - --config override path
    - ConfigNotFoundError when no file found
    - ConfigParseError on invalid YAML
    - ConfigValidationError on missing required fields
    - ConfigValidationError on malformed commands
    - Ship section: enabled=false skips validation of user/host/path
    - Ship section: missing required fields when enabled=true
    - Destination defaults to /tmp when not specified
"""

import os
from pathlib import Path

import pytest
import yaml

from packkit.config import PackConfig, ShipConfig, load_config
from packkit.exceptions import (
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)


# -----------------------------------------------------------------------------
# Happy path — minimal config
# -----------------------------------------------------------------------------

class TestMinimalConfig:
    """Minimal config loads and validates correctly."""

    def test_returns_pack_config(self, minimal_yaml):
        """load_config returns a PackConfig instance."""
        result = load_config(str(minimal_yaml))
        assert isinstance(result, PackConfig)

    def test_pack_name(self, minimal_yaml):
        """pack_name is loaded correctly."""
        result = load_config(str(minimal_yaml))
        assert result.pack_name == 'test-server'

    def test_destination_is_path(self, minimal_yaml):
        """destination is a resolved Path."""
        result = load_config(str(minimal_yaml))
        assert isinstance(result.destination, Path)

    def test_empty_files_list(self, minimal_yaml):
        """files defaults to empty list."""
        result = load_config(str(minimal_yaml))
        assert result.files == []

    def test_empty_directories_list(self, minimal_yaml):
        """directories defaults to empty list."""
        result = load_config(str(minimal_yaml))
        assert result.directories == []

    def test_empty_commands_list(self, minimal_yaml):
        """commands defaults to empty list."""
        result = load_config(str(minimal_yaml))
        assert result.commands == []

    def test_ship_is_none(self, minimal_yaml):
        """ship is None when not specified."""
        result = load_config(str(minimal_yaml))
        assert result.ship is None


# -----------------------------------------------------------------------------
# Happy path — full config
# -----------------------------------------------------------------------------

class TestFullConfig:
    """Full config with all sections loads correctly."""

    def test_files_loaded(self, full_yaml):
        """files list is populated."""
        result = load_config(str(full_yaml))
        assert len(result.files) == 2

    def test_files_are_paths(self, full_yaml):
        """file entries are Path instances."""
        result = load_config(str(full_yaml))
        assert all(isinstance(f, Path) for f in result.files)

    def test_directories_loaded(self, full_yaml):
        """directories list is populated."""
        result = load_config(str(full_yaml))
        assert len(result.directories) == 1

    def test_commands_loaded(self, full_yaml):
        """commands list is populated."""
        result = load_config(str(full_yaml))
        assert len(result.commands) == 2

    def test_command_label(self, full_yaml):
        """command label is loaded correctly."""
        result = load_config(str(full_yaml))
        assert result.commands[0].label == 'os-release'

    def test_command_run(self, full_yaml):
        """command run string is loaded correctly."""
        result = load_config(str(full_yaml))
        assert result.commands[0].run == 'cat /etc/os-release'

    def test_ship_loaded(self, full_yaml):
        """ship section produces a ShipConfig."""
        result = load_config(str(full_yaml))
        assert isinstance(result.ship, ShipConfig)

    def test_ship_enabled(self, full_yaml):
        """ship.enabled is True."""
        result = load_config(str(full_yaml))
        assert result.ship.enabled is True

    def test_ship_user(self, full_yaml):
        """ship.user is loaded correctly."""
        result = load_config(str(full_yaml))
        assert result.ship.user == 'carolyn'

    def test_ship_host(self, full_yaml):
        """ship.host is loaded correctly."""
        result = load_config(str(full_yaml))
        assert result.ship.host == '192.168.10.2'

    def test_ship_path(self, full_yaml):
        """ship.path is loaded correctly."""
        result = load_config(str(full_yaml))
        assert result.ship.path == '/srv/backups'


# -----------------------------------------------------------------------------
# Default config file lookup
# -----------------------------------------------------------------------------

class TestDefaultLookup:
    """load_config finds packkit.yaml in the current directory by default."""

    def test_finds_packkit_yaml_in_cwd(self, tmp_path, minimal_yaml, monkeypatch):
        """load_config finds packkit.yaml when called with no argument."""
        monkeypatch.chdir(tmp_path)
        result = load_config()
        assert result.pack_name == 'test-server'

    def test_raises_when_no_yaml_in_cwd(self, tmp_path, monkeypatch):
        """ConfigNotFoundError raised when no packkit.yaml in cwd."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ConfigNotFoundError):
            load_config()


# -----------------------------------------------------------------------------
# Destination default
# -----------------------------------------------------------------------------

class TestDestinationDefault:
    """destination defaults to /tmp when not specified."""

    def test_destination_defaults_to_tmp(self, tmp_path):
        """When destination is omitted, it defaults to /tmp."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(
            yaml.dump({'pack_name': 'test-server'}),
            encoding='utf-8',
        )
        result = load_config(str(config_file))
        assert result.destination == Path('/tmp')


# -----------------------------------------------------------------------------
# Error cases
# -----------------------------------------------------------------------------

class TestConfigNotFound:
    """ConfigNotFoundError on missing config files."""

    def test_explicit_path_not_found(self, tmp_path):
        """ConfigNotFoundError when explicit path does not exist."""
        with pytest.raises(ConfigNotFoundError):
            load_config(str(tmp_path / 'does_not_exist.yaml'))

    def test_explicit_path_is_directory(self, tmp_path):
        """ConfigNotFoundError when explicit path is a directory."""
        with pytest.raises(ConfigNotFoundError):
            load_config(str(tmp_path))


class TestConfigParseError:
    """ConfigParseError on invalid YAML."""

    def test_invalid_yaml(self, tmp_path):
        """ConfigParseError on malformed YAML."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text('key: [unclosed bracket\n', encoding='utf-8')
        with pytest.raises(ConfigParseError):
            load_config(str(config_file))

    def test_yaml_not_a_mapping(self, tmp_path):
        """ConfigParseError when YAML root is not a mapping."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text('- item1\n- item2\n', encoding='utf-8')
        with pytest.raises(ConfigParseError):
            load_config(str(config_file))


class TestConfigValidationError:
    """ConfigValidationError on structurally invalid configs."""

    def test_missing_pack_name(self, tmp_path):
        """ConfigValidationError when pack_name is missing."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump({'destination': '/tmp'}), encoding='utf-8')
        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_empty_pack_name(self, tmp_path):
        """ConfigValidationError when pack_name is empty string."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump({'pack_name': '  '}), encoding='utf-8')
        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_command_missing_label(self, tmp_path):
        """ConfigValidationError when a command entry has no label."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(
            yaml.dump({'pack_name': 'test', 'commands': [{'run': 'uname -r'}]}),
            encoding='utf-8',
        )
        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_command_missing_run(self, tmp_path):
        """ConfigValidationError when a command entry has no run string."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(
            yaml.dump({'pack_name': 'test', 'commands': [{'label': 'kernel'}]}),
            encoding='utf-8',
        )
        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_ship_enabled_missing_user(self, tmp_path):
        """ConfigValidationError when ship.enabled=true but user is missing."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(
            yaml.dump({
                'pack_name': 'test',
                'ship': {'enabled': True, 'host': '192.168.1.1', 'path': '/backups'},
            }),
            encoding='utf-8',
        )
        with pytest.raises(ConfigValidationError):
            load_config(str(config_file))

    def test_ship_disabled_no_validation(self, tmp_path):
        """No error when ship.enabled=false even if user/host/path are missing."""
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(
            yaml.dump({'pack_name': 'test', 'ship': {'enabled': False}}),
            encoding='utf-8',
        )
        result = load_config(str(config_file))
        assert result.ship is not None
        assert result.ship.enabled is False
```

---

## test_collector.py

```python
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
```

---

## test_packer.py

```python
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
```

---

## test_shipper.py

```python
"""
test_shipper.py — Tests for the Shipper class.

Covers:
    - Happy path: scp called with correct arguments
    - Key argument included when ship.key is set
    - Key argument omitted when ship.key is None
    - ScpError raised on non-zero scp exit
    - ScpError raised on scp timeout
    - ScpError raised when scp cannot be executed
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from packkit.config import ShipConfig
from packkit.exceptions import ScpError
from packkit.shipper import Shipper


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def make_ship_config(key=None) -> ShipConfig:
    return ShipConfig(
        enabled=True,
        user='carolyn',
        host='192.168.10.2',
        path='/srv/backups',
        key=key,
    )


def make_completed_process(returncode=0, stderr=''):
    mock = MagicMock()
    mock.returncode = returncode
    mock.stderr = stderr
    return mock


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------

class TestShipperHappyPath:
    """Shipper calls scp with correct arguments."""

    def test_scp_called(self, tmp_path):
        """subprocess.run is called when ship() is invoked."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process()) as mock_run:
            shipper = Shipper(make_ship_config())
            shipper.ship(tarball)
            assert mock_run.called

    def test_scp_destination_format(self, tmp_path):
        """scp destination is user@host:path."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process()) as mock_run:
            shipper = Shipper(make_ship_config())
            shipper.ship(tarball)
            cmd = mock_run.call_args[0][0]
            assert 'carolyn@192.168.10.2:/srv/backups' in cmd

    def test_tarball_path_in_command(self, tmp_path):
        """The tarball path is included in the scp command."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process()) as mock_run:
            shipper = Shipper(make_ship_config())
            shipper.ship(tarball)
            cmd = mock_run.call_args[0][0]
            assert str(tarball) in cmd

    def test_key_included_when_set(self, tmp_path):
        """-i key argument is included when ship.key is set."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process()) as mock_run:
            shipper = Shipper(make_ship_config(key='/home/carolyn/.ssh/id_ed25519'))
            shipper.ship(tarball)
            cmd = mock_run.call_args[0][0]
            assert '-i' in cmd
            assert '/home/carolyn/.ssh/id_ed25519' in cmd

    def test_key_omitted_when_none(self, tmp_path):
        """-i argument is not included when ship.key is None."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process()) as mock_run:
            shipper = Shipper(make_ship_config(key=None))
            shipper.ship(tarball)
            cmd = mock_run.call_args[0][0]
            assert '-i' not in cmd


# -----------------------------------------------------------------------------
# Error cases
# -----------------------------------------------------------------------------

class TestShipperErrors:
    """Shipper raises ScpError on failure."""

    def test_nonzero_exit_raises_scp_error(self, tmp_path):
        """ScpError raised when scp exits non-zero."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process(returncode=1, stderr='Connection refused')):
            shipper = Shipper(make_ship_config())
            with pytest.raises(ScpError):
                shipper.ship(tarball)

    def test_timeout_raises_scp_error(self, tmp_path):
        """ScpError raised on subprocess timeout."""
        import subprocess
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   side_effect=subprocess.TimeoutExpired(cmd='scp', timeout=120)):
            shipper = Shipper(make_ship_config())
            with pytest.raises(ScpError):
                shipper.ship(tarball)

    def test_os_error_raises_scp_error(self, tmp_path):
        """ScpError raised when scp cannot be executed."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   side_effect=OSError('scp not found')):
            shipper = Shipper(make_ship_config())
            with pytest.raises(ScpError):
                shipper.ship(tarball)

    def test_scp_error_message_contains_stderr(self, tmp_path):
        """ScpError message includes stderr output."""
        tarball = tmp_path / 'test-server-20260609.tar.gz'
        tarball.touch()

        with patch('packkit.shipper.subprocess.run',
                   return_value=make_completed_process(returncode=1, stderr='Host unreachable')):
            shipper = Shipper(make_ship_config())
            with pytest.raises(ScpError) as exc_info:
                shipper.ship(tarball)
            assert 'Host unreachable' in str(exc_info.value)
```

---

## test_cli.py

```python
"""
test_cli.py — Tests for the packkit CLI entry point.

Covers:
    - Happy path: exits 0 with minimal config
    - --dry-run: prints summary, exits 0, creates no archive
    - --config flag: loads specified config file
    - Missing config: exits 2 with error message
    - Collector failure: exits 1 with error message, log written
    - Ship called when ship.enabled is true
    - Ship not called when ship.enabled is false
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from packkit.cli import main
from packkit.exceptions import FileCollectionError, ScpError


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def run_main(argv, monkeypatch):
    """Run cli.main() with patched sys.argv."""
    monkeypatch.setattr(sys, 'argv', argv)
    main()


MINIMAL_YAML = {
    'pack_name': 'test-server',
    'destination': None,  # overridden per test
    'files': [],
    'directories': [],
    'commands': [],
}


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------

class TestCliHappyPath:
    """CLI exits 0 on success."""

    def test_exits_zero(self, tmp_path, monkeypatch):
        """Successful run exits 0."""
        config_data = {**MINIMAL_YAML, 'destination': str(tmp_path / 'output')}
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit) as exc_info:
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        assert exc_info.value.code == 0

    def test_tarball_created(self, tmp_path, monkeypatch):
        """Successful run creates a tarball."""
        output_dir = tmp_path / 'output'
        config_data = {**MINIMAL_YAML, 'destination': str(output_dir)}
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit):
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        tarballs = list(output_dir.glob('*.tar.gz'))
        assert len(tarballs) == 1


# -----------------------------------------------------------------------------
# --dry-run
# -----------------------------------------------------------------------------

class TestDryRun:
    """--dry-run prints summary and exits 0 without creating an archive."""

    def test_dry_run_exits_zero(self, tmp_path, monkeypatch, capsys):
        """--dry-run exits 0."""
        config_data = {**MINIMAL_YAML, 'destination': str(tmp_path / 'output')}
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with pytest.raises(SystemExit) as exc_info:
            run_main(['packkit', '--config', str(config_file), '--dry-run'], monkeypatch)

        assert exc_info.value.code == 0

    def test_dry_run_no_tarball(self, tmp_path, monkeypatch):
        """--dry-run does not create a tarball."""
        output_dir = tmp_path / 'output'
        config_data = {**MINIMAL_YAML, 'destination': str(output_dir)}
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with pytest.raises(SystemExit):
            run_main(['packkit', '--config', str(config_file), '--dry-run'], monkeypatch)

        assert not output_dir.exists() or not list(output_dir.glob('*.tar.gz'))

    def test_dry_run_prints_pack_name(self, tmp_path, monkeypatch, capsys):
        """--dry-run prints the pack name."""
        config_data = {**MINIMAL_YAML, 'destination': str(tmp_path / 'output')}
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with pytest.raises(SystemExit):
            run_main(['packkit', '--config', str(config_file), '--dry-run'], monkeypatch)

        out = capsys.readouterr().out
        assert 'test-server' in out


# -----------------------------------------------------------------------------
# --config flag
# -----------------------------------------------------------------------------

class TestConfigFlag:
    """--config flag loads the specified file."""

    def test_config_flag_loads_named_file(self, tmp_path, monkeypatch):
        """--config loads the named config file."""
        config_data = {**MINIMAL_YAML, 'destination': str(tmp_path / 'output'),
                       'pack_name': 'named-server'}
        config_file = tmp_path / 'named.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit) as exc_info:
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        assert exc_info.value.code == 0

    def test_missing_config_exits_two(self, tmp_path, monkeypatch):
        """Missing --config file exits with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            run_main(
                ['packkit', '--config', str(tmp_path / 'does_not_exist.yaml')],
                monkeypatch,
            )
        assert exc_info.value.code == 2

    def test_missing_config_error_to_stderr(self, tmp_path, monkeypatch, capsys):
        """Missing --config file prints error to stderr."""
        with pytest.raises(SystemExit):
            run_main(
                ['packkit', '--config', str(tmp_path / 'does_not_exist.yaml')],
                monkeypatch,
            )
        err = capsys.readouterr().err
        assert 'packkit: error:' in err


# -----------------------------------------------------------------------------
# Collector failure
# -----------------------------------------------------------------------------

class TestCollectorFailure:
    """Collector failure exits 1 and writes log."""

    def test_collector_failure_exits_one(self, tmp_path, monkeypatch):
        """FileCollectionError during pack exits with code 1."""
        hostname_file = tmp_path / 'etc' / 'hostname'
        hostname_file.parent.mkdir()
        hostname_file.write_text('test\n', encoding='utf-8')

        config_data = {
            'pack_name': 'test-server',
            'destination': str(tmp_path / 'output'),
            'files': ['/this/file/absolutely/does/not/exist.txt'],
            'directories': [],
            'commands': [],
        }
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit) as exc_info:
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        assert exc_info.value.code == 1

    def test_collector_failure_error_to_stderr(self, tmp_path, monkeypatch, capsys):
        """Collector failure prints error to stderr."""
        config_data = {
            'pack_name': 'test-server',
            'destination': str(tmp_path / 'output'),
            'files': ['/this/file/absolutely/does/not/exist.txt'],
            'directories': [],
            'commands': [],
        }
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit):
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        err = capsys.readouterr().err
        assert 'packkit: error:' in err


# -----------------------------------------------------------------------------
# Ship behaviour
# -----------------------------------------------------------------------------

class TestShipBehaviour:
    """Shipper is called only when ship.enabled is true."""

    def test_shipper_called_when_enabled(self, tmp_path, monkeypatch):
        """Shipper.ship() is called when ship.enabled=true."""
        config_data = {
            'pack_name': 'test-server',
            'destination': str(tmp_path / 'output'),
            'files': [],
            'directories': [],
            'commands': [],
            'ship': {
                'enabled': True,
                'user': 'carolyn',
                'host': '192.168.10.2',
                'path': '/srv/backups',
            },
        }
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.shipper.Shipper.ship') as mock_ship, \
             patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit):
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        assert mock_ship.called

    def test_shipper_not_called_when_disabled(self, tmp_path, monkeypatch):
        """Shipper.ship() is not called when ship.enabled=false."""
        config_data = {
            'pack_name': 'test-server',
            'destination': str(tmp_path / 'output'),
            'files': [],
            'directories': [],
            'commands': [],
            'ship': {'enabled': False},
        }
        config_file = tmp_path / 'packkit.yaml'
        config_file.write_text(yaml.dump(config_data), encoding='utf-8')

        with patch('packkit.shipper.Shipper.ship') as mock_ship, \
             patch('packkit.logger.RunLogger._write'):
            with pytest.raises(SystemExit):
                run_main(['packkit', '--config', str(config_file)], monkeypatch)

        assert not mock_ship.called
```

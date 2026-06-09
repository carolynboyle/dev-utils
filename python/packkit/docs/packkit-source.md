# pack-kit source modules
# All files go under python/packkit/src/packkit/

---

## config.py

```python
"""
config.py — Configuration loader and validator for pack-kit.

Loads packkit.yaml from the current directory or a specified path,
validates its structure, and returns a PackConfig dataclass for use
by the rest of the tool.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from packkit.exceptions import (
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)

DEFAULT_CONFIG_NAME = 'packkit.yaml'


@dataclass
class ShipConfig:
    """Remote transfer configuration."""
    enabled: bool
    user: str
    host: str
    path: str
    key: Optional[str] = None


@dataclass
class CommandConfig:
    """A single command to run and capture."""
    label: str
    run: str


@dataclass
class PackConfig:
    """Validated, fully resolved pack-kit configuration."""
    pack_name: str
    destination: Path
    files: list[Path]
    directories: list[Path]
    commands: list[CommandConfig]
    ship: Optional[ShipConfig]


def load_config(config_path: Optional[str] = None) -> PackConfig:
    """
    Load and validate pack-kit configuration.

    Looks for packkit.yaml in the current directory if config_path is None.
    Raises ConfigNotFoundError if no config file can be found.
    Raises ConfigParseError if the file is not valid YAML.
    Raises ConfigValidationError if required fields are missing or invalid.

    Args:
        config_path: Explicit path to a config file, or None to use default.

    Returns:
        Validated PackConfig instance.
    """
    path = _resolve_path(config_path)
    raw = _read_yaml(path)
    return _validate(raw, path)


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------

def _resolve_path(config_path: Optional[str]) -> Path:
    """
    Resolve the config file path.

    Args:
        config_path: Explicit path string or None.

    Returns:
        Resolved Path to the config file.

    Raises:
        ConfigNotFoundError: If the file cannot be found.
    """
    if config_path is not None:
        p = Path(config_path).expanduser().resolve()
        if not p.exists():
            raise ConfigNotFoundError(f"Config file not found: {p}")
        if not p.is_file():
            raise ConfigNotFoundError(f"Config path is not a file: {p}")
        return p

    default = Path.cwd() / DEFAULT_CONFIG_NAME
    if not default.exists():
        raise ConfigNotFoundError(
            f"No config file specified and no {DEFAULT_CONFIG_NAME} found in {Path.cwd()}"
        )
    return default


def _read_yaml(path: Path) -> dict:
    """
    Read and parse a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML as a dict.

    Raises:
        ConfigParseError: If the file cannot be read or parsed.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ConfigParseError(f"Could not read config file {path}: {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigParseError(f"Could not parse config file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigParseError(f"Config file {path} did not parse to a mapping")

    return data


def _validate(data: dict, path: Path) -> PackConfig:
    """
    Validate parsed YAML and return a PackConfig.

    Args:
        data: Parsed YAML dict.
        path: Source path (used in error messages).

    Returns:
        Validated PackConfig.

    Raises:
        ConfigValidationError: If required fields are missing or have wrong types.
    """
    def _require(key: str) -> object:
        if key not in data:
            raise ConfigValidationError(f"Required field '{key}' missing in {path}")
        return data[key]

    pack_name = _require('pack_name')
    if not isinstance(pack_name, str) or not pack_name.strip():
        raise ConfigValidationError(f"'pack_name' must be a non-empty string in {path}")

    destination = Path(str(data.get('destination', '/tmp'))).expanduser().resolve()

    files = []
    for entry in data.get('files', []):
        files.append(Path(str(entry)).expanduser())

    directories = []
    for entry in data.get('directories', []):
        directories.append(Path(str(entry)).expanduser())

    commands = []
    for entry in data.get('commands', []):
        if not isinstance(entry, dict):
            raise ConfigValidationError(f"Each command entry must be a mapping in {path}")
        if 'label' not in entry or 'run' not in entry:
            raise ConfigValidationError(
                f"Command entries require 'label' and 'run' fields in {path}"
            )
        commands.append(CommandConfig(label=str(entry['label']), run=str(entry['run'])))

    ship = None
    if 'ship' in data:
        ship = _validate_ship(data['ship'], path)

    return PackConfig(
        pack_name=pack_name.strip(),
        destination=destination,
        files=files,
        directories=directories,
        commands=commands,
        ship=ship,
    )


def _validate_ship(data: dict, path: Path) -> ShipConfig:
    """
    Validate the ship section of the config.

    Args:
        data: The ship sub-dict.
        path: Source path (used in error messages).

    Returns:
        Validated ShipConfig.

    Raises:
        ConfigValidationError: If required ship fields are missing.
    """
    if not isinstance(data, dict):
        raise ConfigValidationError(f"'ship' must be a mapping in {path}")

    enabled = bool(data.get('enabled', False))
    if not enabled:
        return ShipConfig(enabled=False, user='', host='', path='')

    for key in ('user', 'host', 'path'):
        if key not in data:
            raise ConfigValidationError(
                f"'ship.{key}' is required when ship.enabled is true in {path}"
            )

    key_path = data.get('key')
    if key_path is not None:
        key_path = str(Path(str(key_path)).expanduser())

    return ShipConfig(
        enabled=True,
        user=str(data['user']),
        host=str(data['host']),
        path=str(data['path']),
        key=key_path,
    )
```

---

## collector.py

```python
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
```

---

## packer.py

```python
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
```

---

## logger.py

```python
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
```

---

## shipper.py

```python
"""
shipper.py — Optional remote transfer for pack-kit.

Transfers the completed tarball to a remote host via scp.
Only runs when ship.enabled is true in the config.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from packkit.config import ShipConfig
from packkit.exceptions import ScpError


class Shipper:
    """
    Transfers a tarball to a remote host via scp.

    Args:
        ship_config: Validated ShipConfig.
    """

    def __init__(self, ship_config: ShipConfig) -> None:
        self._config = ship_config

    def ship(self, tarball: Path) -> None:
        """
        Transfer the tarball to the configured remote host.

        Args:
            tarball: Path to the local tarball to transfer.

        Raises:
            ScpError: If the transfer fails or scp cannot be executed.
        """
        destination = f"{self._config.user}@{self._config.host}:{self._config.path}"

        cmd = ['scp']
        if self._config.key:
            cmd += ['-i', self._config.key]
        cmd += [str(tarball), destination]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise ScpError(
                f"scp transfer timed out after 120 seconds to {destination}"
            ) from exc
        except OSError as exc:
            raise ScpError(f"Could not execute scp: {exc}") from exc

        if result.returncode != 0:
            raise ScpError(
                f"scp transfer failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )
```

---

## cli.py

```python
"""
cli.py — Command-line entry point for pack-kit.

Loads configuration, runs the pack, and optionally ships the result
to a remote host.

Usage:
    packkit
    packkit --config /path/to/packkit.yaml
    packkit --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packkit.config import load_config
from packkit.exceptions import (
    CollectorError,
    ConfigError,
    LogError,
    PackerError,
    PackkitError,
    ShipperError,
)
from packkit.logger import RunLogger
from packkit.packer import Packer
from packkit.shipper import Shipper


_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_BAD_ARGS = 2


def main() -> None:
    """Entry point — load config, run pack, ship if configured."""
    args = _parse_args()

    # --- Load config ---------------------------------------------------------
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        _error(str(exc))
        sys.exit(_EXIT_BAD_ARGS)

    logger = RunLogger(config.pack_name)

    # --- Dry run -------------------------------------------------------------
    if args.dry_run:
        _print_dry_run(config)
        sys.exit(_EXIT_OK)

    # --- Pack ----------------------------------------------------------------
    packer = Packer(config, logger)
    try:
        tarball = packer.run()
    except (CollectorError, PackerError) as exc:
        logger.log(f"FAILED: {exc}")
        try:
            logger.close(success=False)
        except LogError as log_exc:
            _error(f"Log write failed: {log_exc}")
        _error(str(exc))
        sys.exit(_EXIT_ERROR)

    # --- Ship ----------------------------------------------------------------
    if config.ship and config.ship.enabled:
        logger.log(
            f"Shipping to {config.ship.user}@{config.ship.host}:{config.ship.path}"
        )
        shipper = Shipper(config.ship)
        try:
            shipper.ship(tarball)
            logger.log("Transfer complete.")
        except ShipperError as exc:
            logger.log(f"FAILED: {exc}")
            try:
                logger.close(success=False)
            except LogError as log_exc:
                _error(f"Log write failed: {log_exc}")
            _error(str(exc))
            sys.exit(_EXIT_ERROR)

    # --- Done ----------------------------------------------------------------
    try:
        logger.close(success=True)
    except LogError as exc:
        _error(f"Log write failed: {exc}")
        sys.exit(_EXIT_ERROR)

    sys.exit(_EXIT_OK)


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """
    Build and return the parsed argument namespace.

    Returns:
        Parsed argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        prog='packkit',
        description='Pack and optionally ship server configuration archives.',
    )
    parser.add_argument(
        '--config', '-c',
        default=None,
        metavar='FILE',
        help='Path to packkit.yaml. Defaults to packkit.yaml in the current directory.',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Print what would be collected without creating an archive.',
    )
    return parser.parse_args()


def _print_dry_run(config) -> None:
    """Print a dry-run summary of what would be collected."""
    print(f"\nDry run — pack: {config.pack_name}")
    print(f"Destination:    {config.destination}\n")

    if config.files:
        print("Files:")
        for f in config.files:
            print(f"  {f}")

    if config.directories:
        print("\nDirectories:")
        for d in config.directories:
            print(f"  {d}")

    if config.commands:
        print("\nCommands:")
        for cmd in config.commands:
            print(f"  [{cmd.label}] {cmd.run}")

    if config.ship and config.ship.enabled:
        print(f"\nShip to: {config.ship.user}@{config.ship.host}:{config.ship.path}")

    print()


def _error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"packkit: error: {message}", file=sys.stderr)
```

---

## __init__.py

```python
"""
packkit — Pack and ship server configuration archives.

Public API:
    load_config  — load and validate a packkit.yaml config file
    Packer       — orchestrates collection and archiving
    Collector    — collects files, directories, and command output
    Shipper      — transfers archives to a remote host
    RunLogger    — run logger and report writer

Exceptions:
    PackkitError            — base class for all packkit exceptions
    ConfigError             — base class for config exceptions
    ConfigNotFoundError     — config file not found
    ConfigParseError        — config file could not be parsed
    ConfigValidationError   — config file failed validation
    CollectorError          — base class for collector exceptions
    FileCollectionError     — file not found or unreadable
    DirectoryCollectionError — directory not found or unreadable
    CommandError            — command failed or timed out
    PackerError             — base class for packer exceptions
    StagingError            — staging directory could not be created
    ArchiveError            — tarball could not be created
    ShipperError            — base class for shipper exceptions
    ScpError                — scp transfer failed
    LogError                — log write failed
"""

from packkit.collector import Collector
from packkit.config import load_config
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
from packkit.logger import RunLogger
from packkit.packer import Packer
from packkit.shipper import Shipper

__all__ = [
    'load_config',
    'Packer',
    'Collector',
    'Shipper',
    'RunLogger',
    'PackkitError',
    'ConfigError',
    'ConfigNotFoundError',
    'ConfigParseError',
    'ConfigValidationError',
    'CollectorError',
    'FileCollectionError',
    'DirectoryCollectionError',
    'CommandError',
    'PackerError',
    'StagingError',
    'ArchiveError',
    'ShipperError',
    'ScpError',
    'LogError',
]
```

---

## data/packkit.yaml.template

```yaml
# packkit.yaml — pack-kit configuration template
# Copy to your working directory, rename to packkit.yaml, and edit.

pack_name: my-server             # used as the tarball base name
destination: /tmp                # where the tarball is created locally

files:
  - /etc/ssh/sshd_config
  - /etc/hostname
  # add individual files here

directories:
  - /etc/myapp                   # entire directory tree will be copied
  # add directories here

commands:
  - label: os-release
    run: cat /etc/os-release
  - label: installed-packages-rpm
    run: rpm -qa
  # - label: installed-packages-deb
  #   run: dpkg -l
  - label: firewall-rules
    run: firewall-cmd --list-all
  # add commands here

ship:
  enabled: false
  user: carolyn
  host: 192.168.10.2
  path: /srv/exports/storage/backups
  key: ~/.ssh/id_ed25519         # omit to use ssh agent
```

---

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "packkit"
version = "0.1.0"
description = "Pack and ship server configuration archives."
readme = "README.md"
requires-python = ">=3.11"
license = { file = "LICENSE" }
authors = [
    { name = "Carolyn Boyle" }
]
dependencies = [
    "pyyaml>=6.0",
]

[project.scripts]
packkit = "packkit.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
packkit = ["data/*.yaml.template"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.pylint.format]
max-line-length = 120

[tool.pylint.messages_control]
disable = ["too-few-public-methods"]
```

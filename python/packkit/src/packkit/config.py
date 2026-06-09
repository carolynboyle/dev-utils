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
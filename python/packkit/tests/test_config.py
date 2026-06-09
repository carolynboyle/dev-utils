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

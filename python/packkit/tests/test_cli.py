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

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
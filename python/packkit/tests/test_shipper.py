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

"""
tests/test_launcher.py - Tests for pxkit.launcher.

Covers Proxmox web UI opening, SPICE temp file writing and cleanup,
remote-viewer launch, and SSH stub behaviour.
subprocess and webbrowser are mocked throughout.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from pxkit.launcher import Launcher
from pxkit.exceptions import PxkitLaunchError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    """Return a mock ConfigManager with sensible defaults."""
    config = MagicMock()
    config.proxmox = {
        "host": "localhost",
        "port": 8006,
    }
    config.get.return_value = {
        "app": "xfce4-terminal",
        "exec_flag": "-e",
    }
    return config


@pytest.fixture
def spice_vm():
    """Return a minimal SPICE VM dict."""
    return {
        "name": "Puppy Linux",
        "vmid": 100,
        "connection": {
            "type": "spice",
            "host": "localhost",
        },
    }


@pytest.fixture
def ssh_vm():
    """Return a minimal SSH VM dict."""
    return {
        "name": "Remote SSH",
        "vmid": None,
        "connection": {
            "type": "ssh",
            "host": "192.168.1.50",
            "user": "carolyn",
            "key": "~/.ssh/keys/thinkcentre/ssh",
        },
    }


SAMPLE_VV = "[virt-viewer]\ntype=spice\nhost=localhost\nport=61000\n"


# ---------------------------------------------------------------------------
# open_proxmox_ui
# ---------------------------------------------------------------------------

class TestOpenProxmoxUi:

    def test_opens_correct_url(self, mock_config):
        """Opens the correct Proxmox web UI URL."""
        launcher = Launcher(mock_config)
        with patch("pxkit.launcher.webbrowser.open") as mock_open_browser:
            launcher.open_proxmox_ui()
        mock_open_browser.assert_called_once_with("https://localhost:8006")

    def test_uses_host_and_port_from_config(self, mock_config):
        """URL is built from config host and port."""
        mock_config.proxmox = {"host": "192.168.1.100", "port": 8007}
        launcher = Launcher(mock_config)
        with patch("pxkit.launcher.webbrowser.open") as mock_open_browser:
            launcher.open_proxmox_ui()
        mock_open_browser.assert_called_once_with("https://192.168.1.100:8007")

    def test_raises_on_browser_failure(self, mock_config):
        """Raises PxkitLaunchError when webbrowser.open fails."""
        launcher = Launcher(mock_config)
        with patch("pxkit.launcher.webbrowser.open", side_effect=Exception("no browser")):
            with pytest.raises(PxkitLaunchError, match="Failed to open Proxmox web UI"):
                launcher.open_proxmox_ui()


# ---------------------------------------------------------------------------
# _write_temp_vv
# ---------------------------------------------------------------------------

class TestWriteTempVv:

    def test_returns_path(self, tmp_path):
        """Returns a Path to the written temp file."""
        result = Launcher._write_temp_vv(SAMPLE_VV)
        assert isinstance(result, Path)
        assert result.exists()
        result.unlink()

    def test_file_contains_vv_content(self, tmp_path):
        """Written file contains the expected .vv content."""
        result = Launcher._write_temp_vv(SAMPLE_VV)
        assert result.read_text(encoding="utf-8") == SAMPLE_VV
        result.unlink()

    def test_file_has_vv_suffix(self):
        """Temp file has .vv suffix."""
        result = Launcher._write_temp_vv(SAMPLE_VV)
        assert result.suffix == ".vv"
        result.unlink()


# ---------------------------------------------------------------------------
# _cleanup_temp
# ---------------------------------------------------------------------------

class TestCleanupTemp:

    def test_deletes_existing_file(self, tmp_path):
        """Deletes a file that exists."""
        p = tmp_path / "test.vv"
        p.write_text("content", encoding="utf-8")
        Launcher._cleanup_temp(p)
        assert not p.exists()

    def test_does_not_raise_for_missing_file(self, tmp_path):
        """Does not raise if file is already gone."""
        p = tmp_path / "nonexistent.vv"
        Launcher._cleanup_temp(p)  # should not raise


# ---------------------------------------------------------------------------
# launch_spice
# ---------------------------------------------------------------------------

class TestLaunchSpice:

    def test_launches_remote_viewer(self, mock_config):
        """Calls remote-viewer with the temp file path."""
        launcher = Launcher(mock_config)
        fake_path = Path("/tmp/fake.vv")

        with (
            patch.object(Launcher, "_write_temp_vv", return_value=fake_path),
            patch.object(Launcher, "_cleanup_temp"),
            patch("pxkit.launcher.subprocess.Popen") as mock_popen,
        ):
            launcher.launch_spice(SAMPLE_VV)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "remote-viewer"
        assert str(fake_path) in call_args

    def test_cleans_up_temp_file_on_success(self, mock_config):
        """Temp file is cleaned up after successful launch."""
        launcher = Launcher(mock_config)
        fake_path = Path("/tmp/fake.vv")

        with (
            patch.object(Launcher, "_write_temp_vv", return_value=fake_path),
            patch.object(Launcher, "_cleanup_temp") as mock_cleanup,
            patch("pxkit.launcher.subprocess.Popen"),
        ):
            launcher.launch_spice(SAMPLE_VV)

        mock_cleanup.assert_called_once_with(fake_path)

    def test_cleans_up_temp_file_on_failure(self, mock_config):
        """Temp file is cleaned up even when remote-viewer launch fails."""
        launcher = Launcher(mock_config)
        fake_path = Path("/tmp/fake.vv")

        with (
            patch.object(Launcher, "_write_temp_vv", return_value=fake_path),
            patch.object(Launcher, "_cleanup_temp") as mock_cleanup,
            patch("pxkit.launcher.subprocess.Popen", side_effect=OSError("fail")),
        ):
            with pytest.raises(PxkitLaunchError):
                launcher.launch_spice(SAMPLE_VV)

        mock_cleanup.assert_called_once_with(fake_path)

    def test_raises_when_remote_viewer_not_found(self, mock_config):
        """Raises PxkitLaunchError with install hint when remote-viewer is missing."""
        launcher = Launcher(mock_config)
        fake_path = Path("/tmp/fake.vv")

        with (
            patch.object(Launcher, "_write_temp_vv", return_value=fake_path),
            patch.object(Launcher, "_cleanup_temp"),
            patch("pxkit.launcher.subprocess.Popen", side_effect=FileNotFoundError()),
        ):
            with pytest.raises(PxkitLaunchError, match="apt install virt-viewer"):
                launcher.launch_spice(SAMPLE_VV)


# ---------------------------------------------------------------------------
# launch_ssh (stub)
# ---------------------------------------------------------------------------

class TestLaunchSsh:

    def test_raises_not_implemented(self, mock_config, ssh_vm):
        """SSH launch raises PxkitLaunchError as not yet implemented."""
        launcher = Launcher(mock_config)
        with pytest.raises(PxkitLaunchError, match="not yet implemented"):
            launcher.launch_ssh(ssh_vm)

    def test_error_includes_vm_name(self, mock_config, ssh_vm):
        """Error message includes the VM name."""
        launcher = Launcher(mock_config)
        with pytest.raises(PxkitLaunchError, match="Remote SSH"):
            launcher.launch_ssh(ssh_vm)

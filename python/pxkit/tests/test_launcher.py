"""
tests/test_launcher.py - Tests for pxkit.launcher.

Covers Proxmox web UI opening, SPICE stdin pipe launch, and SSH stub behaviour.
subprocess and webbrowser are mocked throughout.
"""

from unittest.mock import MagicMock, patch, call

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
    return config


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


SAMPLE_VV = "[virt-viewer]\ntype=spice\nhost=pvespiceproxy:abc:100:node:61000::fp\npassword=secret\n"


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
# launch_spice
# ---------------------------------------------------------------------------

class TestLaunchSpice:

    def test_launches_remote_viewer_via_stdin(self, mock_config):
        """Calls remote-viewer with '-' (stdin) argument."""
        launcher = Launcher(mock_config)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()

        with patch("pxkit.launcher.subprocess.Popen", return_value=mock_process) as mock_popen:
            launcher.launch_spice(SAMPLE_VV)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "remote-viewer"
        assert "-" in call_args

    def test_pipes_vv_content_to_stdin(self, mock_config):
        """Writes .vv content to remote-viewer's stdin."""
        launcher = Launcher(mock_config)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()

        with patch("pxkit.launcher.subprocess.Popen", return_value=mock_process):
            launcher.launch_spice(SAMPLE_VV)

        mock_process.stdin.write.assert_called_once_with(SAMPLE_VV.encode("utf-8"))
        mock_process.stdin.close.assert_called_once()

    def test_raises_when_remote_viewer_not_found(self, mock_config):
        """Raises PxkitLaunchError with install hint when remote-viewer is missing."""
        launcher = Launcher(mock_config)
        with patch("pxkit.launcher.subprocess.Popen", side_effect=FileNotFoundError()):
            with pytest.raises(PxkitLaunchError, match="apt install virt-viewer"):
                launcher.launch_spice(SAMPLE_VV)

    def test_raises_on_os_error(self, mock_config):
        """Raises PxkitLaunchError on OSError."""
        launcher = Launcher(mock_config)
        with patch("pxkit.launcher.subprocess.Popen", side_effect=OSError("fail")):
            with pytest.raises(PxkitLaunchError, match="Failed to launch remote-viewer"):
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

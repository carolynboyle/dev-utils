"""
tests/test_launcher.py - Tests for nmkit.launcher.

Covers .nxs template rendering, temp file writing and cleanup,
and nxclient subprocess launch. subprocess is mocked throughout.
No real processes are started.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nmkit.launcher import Launcher
from nmkit.exceptions import NmkitLaunchError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    """Return a mock ConfigManager with sensible defaults."""
    config = MagicMock()
    config.app = {"nxclient": "/usr/NX/bin/nxclient"}
    return config


@pytest.fixture
def rocky_connection():
    """Return a minimal Rocky Linux connection dict."""
    return {
        "name": "Rocky",
        "host": "100.64.0.17",
        "port": 22,
        "user": "carolyn",
        "os": "rocky",
    }


@pytest.fixture
def debian_connection():
    """Return a minimal Debian connection dict."""
    return {
        "name": "wcyjv25",
        "host": "100.64.0.18",
        "port": 22,
        "user": "carolyn",
        "os": "debian",
    }


# ---------------------------------------------------------------------------
# _render_nxs
# ---------------------------------------------------------------------------

class TestRenderNxs:

    def test_host_substituted(self, mock_config, rocky_connection):
        """Host is substituted correctly in the .nxs template."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        assert 'value="100.64.0.17"' in result

    def test_port_substituted(self, mock_config, rocky_connection):
        """Port is substituted correctly in the .nxs template."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        assert 'key="Server port" value="22"' in result

    def test_user_substituted(self, mock_config, rocky_connection):
        """User is substituted correctly in the .nxs template."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        assert 'key="User" value="carolyn"' in result

    def test_auth_absent(self, mock_config, rocky_connection):
        """Auth key is not present in generated .nxs (no stored credentials)."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        # Auth key must not appear with a real value
        assert 'key="Auth" value="' not in result

    def test_node_uuid_blank(self, mock_config, rocky_connection):
        """Node UUID is blank in generated .nxs."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        assert 'key="Node UUID" value=""' in result

    def test_output_is_valid_xml_start(self, mock_config, rocky_connection):
        """Generated output starts with the DOCTYPE declaration."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(rocky_connection)
        assert result.startswith("<!DOCTYPE NXClientSettings>")

    def test_different_connections_produce_different_output(
        self, mock_config, rocky_connection, debian_connection
    ):
        """Different connections produce different .nxs content."""
        launcher = Launcher(mock_config)
        rocky  = launcher._render_nxs(rocky_connection)
        debian = launcher._render_nxs(debian_connection)
        assert rocky != debian


# ---------------------------------------------------------------------------
# _write_temp_nxs
# ---------------------------------------------------------------------------

class TestWriteTempNxs:

    SAMPLE_NXS = "<!DOCTYPE NXClientSettings>\n<NXClientSettings />\n"

    def test_returns_path(self):
        """Returns a Path to the written temp file."""
        result = Launcher._write_temp_nxs(self.SAMPLE_NXS)
        assert isinstance(result, Path)
        assert result.exists()
        result.unlink()

    def test_file_has_nxs_suffix(self):
        """Temp file has .nxs suffix."""
        result = Launcher._write_temp_nxs(self.SAMPLE_NXS)
        assert result.suffix == ".nxs"
        result.unlink()

    def test_file_contains_correct_content(self):
        """Written file contains the expected .nxs content."""
        result = Launcher._write_temp_nxs(self.SAMPLE_NXS)
        assert result.read_text(encoding="utf-8") == self.SAMPLE_NXS
        result.unlink()


# ---------------------------------------------------------------------------
# _start_nxclient
# ---------------------------------------------------------------------------

class TestStartNxclient:

    def test_calls_popen_with_session_flag(self, mock_config, tmp_path):
        """Calls Popen with --session and the .nxs path."""
        launcher  = Launcher(mock_config)
        nxs_path  = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher._start_nxclient(nxs_path)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "/usr/NX/bin/nxclient"
        assert "--session" in call_args
        assert str(nxs_path) in call_args

    def test_raises_when_nxclient_not_found(self, mock_config, tmp_path):
        """Raises NmkitLaunchError with helpful message when nxclient missing."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch(
            "nmkit.launcher.subprocess.Popen",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(NmkitLaunchError, match="nxclient not found"):
                launcher._start_nxclient(nxs_path)

    def test_raises_on_oserror(self, mock_config, tmp_path):
        """Raises NmkitLaunchError on generic OSError."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch(
            "nmkit.launcher.subprocess.Popen",
            side_effect=OSError("permission denied"),
        ):
            with pytest.raises(NmkitLaunchError, match="Failed to start nxclient"):
                launcher._start_nxclient(nxs_path)

    def test_uses_nxclient_path_from_config(self, tmp_path):
        """Uses the nxclient binary path from the app config."""
        config     = MagicMock()
        config.app = {"nxclient": "/custom/path/nxclient"}
        launcher   = Launcher(config)
        nxs_path    = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher._start_nxclient(nxs_path)

        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "/custom/path/nxclient"


# ---------------------------------------------------------------------------
# launch (integration)
# ---------------------------------------------------------------------------

class TestLaunch:

    def test_temp_file_cleaned_up_on_success(
        self, mock_config, rocky_connection, tmp_path
    ):
        """Temp .nxs file is removed after successful launch."""
        fake_path = tmp_path / "fake.nxs"
        fake_path.write_text("content", encoding="utf-8")

        launcher = Launcher(mock_config)

        with (
            patch.object(Launcher, "_write_temp_nxs", return_value=fake_path),
            patch.object(Launcher, "_start_nxclient"),
        ):
            launcher.launch(rocky_connection)

        assert not fake_path.exists()

    def test_temp_file_cleaned_up_on_failure(
        self, mock_config, rocky_connection, tmp_path
    ):
        """Temp .nxs file is removed even when nxclient launch fails."""
        fake_path = tmp_path / "fake.nxs"
        fake_path.write_text("content", encoding="utf-8")

        launcher = Launcher(mock_config)

        with (
            patch.object(Launcher, "_write_temp_nxs", return_value=fake_path),
            patch.object(
                Launcher, "_start_nxclient",
                side_effect=NmkitLaunchError("fail"),
            ),
        ):
            with pytest.raises(NmkitLaunchError):
                launcher.launch(rocky_connection)

        assert not fake_path.exists()

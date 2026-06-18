"""
tests/test_launcher.py - Tests for nmkit.launcher.

Covers .nxs template rendering, session file writing to the configured
session directory, nxplayer launch, and end-to-end launch() behaviour.
subprocess is mocked throughout; filesystem tests use tmp_path.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from nmkit.launcher import Launcher
from nmkit.exceptions import NmkitLaunchError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_config(nxplayer="/usr/NX/bin/nxplayer", session_dir=None):
    """
    Return a mock ConfigManager whose app property behaves like a real dict.

    config.app is a PropertyMock returning a plain dict, so config.app.get()
    works naturally without trying to override the read-only dict.get method.
    """
    app_dict = {
        "nxplayer":    nxplayer,
        "session_dir": str(session_dir) if session_dir else "/tmp/nmkit-test",
    }
    config      = MagicMock()
    type(config).app = PropertyMock(return_value=app_dict)
    return config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config(tmp_path):
    """Return a mock ConfigManager with sensible defaults."""
    return make_mock_config(session_dir=tmp_path)


@pytest.fixture
def rocky_connection():
    """Return a minimal Rocky Linux connection dict."""
    return {
        "name": "Rocky",
        "host": "192.168.1.10",
        "port": 4000,
        "user": "carolyn",
        "os":   "rocky",
    }


# ---------------------------------------------------------------------------
# _render_nxs
# ---------------------------------------------------------------------------

class TestRenderNxs:

    SAMPLE_CONN = {
        "name": "Test",
        "host": "10.0.0.1",
        "port": 4000,
        "user": "testuser",
        "os":   "debian",
    }

    def test_renders_server_host(self, mock_config):
        """Rendered template contains the connection host."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(self.SAMPLE_CONN)
        assert 'value="10.0.0.1"' in result

    def test_renders_server_port(self, mock_config):
        """Rendered template contains the connection port."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(self.SAMPLE_CONN)
        assert 'value="4000"' in result

    def test_renders_user(self, mock_config):
        """Rendered template contains the connection user."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(self.SAMPLE_CONN)
        assert 'value="testuser"' in result

    def test_is_valid_xml_fragment(self, mock_config):
        """Rendered output starts with the expected XML declaration."""
        launcher = Launcher(mock_config)
        result   = launcher._render_nxs(self.SAMPLE_CONN)
        assert result.startswith("<!DOCTYPE NXClientSettings>")


# ---------------------------------------------------------------------------
# _write_nxs
# ---------------------------------------------------------------------------

class TestWriteNxs:

    SAMPLE_NXS = "<!DOCTYPE NXClientSettings>\n<NXClientSettings />\n"

    def test_returns_path(self, mock_config, tmp_path):
        """Returns a Path to the written session file."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert isinstance(result, Path)

    def test_file_exists(self, mock_config, tmp_path):
        """Written file exists on disk."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.exists()

    def test_file_in_session_dir(self, mock_config, tmp_path):
        """File is written to the configured session directory."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.parent == tmp_path

    def test_filename_uses_connection_name(self, mock_config, tmp_path):
        """Filename is nmkit-{name}.nxs."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.name == "nmkit-Rocky.nxs"

    def test_spaces_in_name_replaced(self, mock_config, tmp_path):
        """Spaces in the connection name are replaced with underscores."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "My Server")
        assert result.name == "nmkit-My_Server.nxs"

    def test_file_has_nxs_suffix(self, mock_config, tmp_path):
        """Written file has .nxs suffix."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.suffix == ".nxs"

    def test_file_contains_content(self, mock_config, tmp_path):
        """Written file contains the expected .nxs content."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.read_text(encoding="utf-8") == self.SAMPLE_NXS

    def test_file_persists(self, mock_config, tmp_path):
        """Written file is not cleaned up by _write_nxs."""
        launcher = Launcher(mock_config)
        result   = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.exists()

    def test_overwrites_existing_file(self, mock_config, tmp_path):
        """Calling _write_nxs twice overwrites the previous file."""
        launcher = Launcher(mock_config)
        launcher._write_nxs("old content", "Rocky")
        result = launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert result.read_text(encoding="utf-8") == self.SAMPLE_NXS

    def test_creates_session_dir_if_missing(self, tmp_path):
        """Creates the session directory if it does not exist."""
        nested_dir = tmp_path / "new" / "subdir"
        config     = make_mock_config(session_dir=nested_dir)
        launcher   = Launcher(config)
        launcher._write_nxs(self.SAMPLE_NXS, "Rocky")
        assert nested_dir.exists()

    def test_raises_on_write_failure(self, mock_config):
        """Raises NmkitLaunchError if the file cannot be written."""
        launcher = Launcher(mock_config)
        with patch("nmkit.launcher.Path.write_text", side_effect=OSError("disk full")):
            with pytest.raises(NmkitLaunchError, match="Could not write .nxs file"):
                launcher._write_nxs(self.SAMPLE_NXS, "Rocky")


# ---------------------------------------------------------------------------
# _start_nxplayer
# ---------------------------------------------------------------------------

class TestStartNxplayer:

    def test_calls_popen_with_config_flag(self, mock_config, tmp_path):
        """Calls Popen with --config and the .nxs path."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher._start_nxplayer(nxs_path)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "/usr/NX/bin/nxplayer"
        assert "--config" in call_args
        assert str(nxs_path) in call_args

    def test_raises_when_nxplayer_not_found(self, mock_config, tmp_path):
        """Raises NmkitLaunchError with helpful message when nxplayer missing."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch(
            "nmkit.launcher.subprocess.Popen",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(NmkitLaunchError, match="nxplayer not found"):
                launcher._start_nxplayer(nxs_path)

    def test_raises_on_oserror(self, mock_config, tmp_path):
        """Raises NmkitLaunchError on generic OSError."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch(
            "nmkit.launcher.subprocess.Popen",
            side_effect=OSError("permission denied"),
        ):
            with pytest.raises(NmkitLaunchError, match="Failed to start nxplayer"):
                launcher._start_nxplayer(nxs_path)

    def test_uses_nxplayer_path_from_config(self, tmp_path):
        """Uses the nxplayer binary path from the app config."""
        config   = make_mock_config(
            nxplayer="/custom/path/nxplayer",
            session_dir=tmp_path,
        )
        launcher = Launcher(config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher._start_nxplayer(nxs_path)

        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == "/custom/path/nxplayer"

    def test_launches_detached(self, mock_config, tmp_path):
        """Popen is called with start_new_session=True."""
        launcher = Launcher(mock_config)
        nxs_path = tmp_path / "test.nxs"
        nxs_path.write_text("content", encoding="utf-8")

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher._start_nxplayer(nxs_path)

        _, kwargs = mock_popen.call_args
        assert kwargs.get("start_new_session") is True


# ---------------------------------------------------------------------------
# launch (integration)
# ---------------------------------------------------------------------------

class TestLaunch:

    def test_writes_nxs_and_launches(self, mock_config, rocky_connection, tmp_path):
        """launch() writes the session file and calls nxplayer."""
        launcher = Launcher(mock_config)

        with patch("nmkit.launcher.subprocess.Popen") as mock_popen:
            launcher.launch(rocky_connection)

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        nxs_path  = tmp_path / "nmkit-Rocky.nxs"
        assert nxs_path.exists()
        assert str(nxs_path) in call_args

    def test_session_file_persists_after_launch(
        self, mock_config, rocky_connection, tmp_path
    ):
        """Session file remains on disk after successful launch."""
        launcher = Launcher(mock_config)

        with patch("nmkit.launcher.subprocess.Popen"):
            launcher.launch(rocky_connection)

        assert (tmp_path / "nmkit-Rocky.nxs").exists()

    def test_raises_on_write_failure(self, mock_config, rocky_connection):
        """Raises NmkitLaunchError when the session file cannot be written."""
        launcher = Launcher(mock_config)

        with patch.object(
            Launcher, "_write_nxs",
            side_effect=NmkitLaunchError("disk full"),
        ):
            with pytest.raises(NmkitLaunchError, match="disk full"):
                launcher.launch(rocky_connection)

    def test_raises_on_nxplayer_not_found(self, mock_config, rocky_connection):
        """Raises NmkitLaunchError when nxplayer binary is missing."""
        launcher = Launcher(mock_config)

        with patch(
            "nmkit.launcher.subprocess.Popen",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(NmkitLaunchError, match="nxplayer not found"):
                launcher.launch(rocky_connection)

    def test_session_dir_from_config(self, rocky_connection, tmp_path):
        """Launcher reads session_dir from config and writes there."""
        custom_dir = tmp_path / "custom_nx_dir"
        config     = make_mock_config(session_dir=custom_dir)
        launcher   = Launcher(config)

        with patch("nmkit.launcher.subprocess.Popen"):
            launcher.launch(rocky_connection)

        assert (custom_dir / "nmkit-Rocky.nxs").exists()

    def test_tilde_expanded_in_session_dir(self, rocky_connection):
        """Tilde in session_dir is expanded to the home directory."""
        config   = make_mock_config(session_dir="~/Documents/NoMachine")
        launcher = Launcher(config)

        assert "~" not in str(launcher._session_dir)
        assert launcher._session_dir.is_absolute()

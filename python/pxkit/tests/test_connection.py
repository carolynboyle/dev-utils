"""
tests/test_connection.py - Tests for pxkit.connection.

Covers SPICE ticket retrieval, connection type validation, proxy
resolution, token secret retrieval, and .vv file formatting.
All external dependencies (keyring, requests) are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from pxkit.connection import ProxmoxConnection
from pxkit.exceptions import PxkitConnectionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_SERVER = {
    "name": "testserver",
    "host": "100.64.0.9",
    "port": 8006,
    "node": "testnode",
    "token_id": "carolyn@pam!pxkit",
}


@pytest.fixture
def mock_config():
    """Return a mock ConfigManager with sensible defaults."""
    config = MagicMock()
    config.servers = [_TEST_SERVER]
    config.get_server.return_value = _TEST_SERVER
    return config


@pytest.fixture
def spice_vm():
    """Return a minimal SPICE VM dict."""
    return {
        "name": "Puppy Linux",
        "vmid": 100,
        "server": "testserver",
        "connection": {
            "type": "spice",
            "host": "100.64.0.9",
            "port": None,
            "security": None,
        },
    }


@pytest.fixture
def ssh_vm():
    """Return a minimal SSH VM dict."""
    return {
        "name": "Remote SSH",
        "vmid": None,
        "server": "testserver",
        "connection": {
            "type": "ssh",
            "host": "100.64.0.9",
            "user": "carolyn",
            "key": "~/.ssh/keys/thinkcentre/ssh",
        },
    }


@pytest.fixture
def tunnel_vm():
    """Return a SPICE VM with SSH tunnel security."""
    return {
        "name": "ThinkCentre Debian",
        "vmid": 203,
        "server": "testserver",
        "connection": {
            "type": "spice",
            "host": "100.64.0.3",
            "port": None,
            "security": {
                "method": "ssh_tunnel",
                "key": "~/.ssh/keys/thinkcentre/spice",
            },
        },
    }


MOCK_SPICE_DATA = {
    "type": "spice",
    "host": "100.64.0.9",
    "port": "61000",
    "password": "secret",
    "tls-port": None,
}


# ---------------------------------------------------------------------------
# _validate_connection_type
# ---------------------------------------------------------------------------

class TestValidateConnectionType:

    def test_passes_for_correct_type(self, mock_config, spice_vm):
        """No exception raised when connection.type matches expected."""
        conn = ProxmoxConnection(mock_config)
        conn._validate_connection_type(spice_vm, expected="spice")  # should not raise

    def test_raises_when_type_missing(self, mock_config):
        """Raises PxkitConnectionError when connection.type is absent."""
        conn = ProxmoxConnection(mock_config)
        vm = {"name": "No Type VM", "vmid": 100, "connection": {"host": "100.64.0.9"}}
        with pytest.raises(PxkitConnectionError, match="no connection.type"):
            conn._validate_connection_type(vm, expected="spice")

    def test_raises_when_type_wrong(self, mock_config, ssh_vm):
        """Raises PxkitConnectionError when connection.type doesn't match expected."""
        conn = ProxmoxConnection(mock_config)
        with pytest.raises(PxkitConnectionError, match="expected 'spice'"):
            conn._validate_connection_type(ssh_vm, expected="spice")

    def test_error_includes_vm_name(self, mock_config):
        """Error message includes the VM name for easy diagnosis."""
        conn = ProxmoxConnection(mock_config)
        vm = {"name": "My VM", "vmid": 100, "connection": {}}
        with pytest.raises(PxkitConnectionError, match="My VM"):
            conn._validate_connection_type(vm, expected="spice")


# ---------------------------------------------------------------------------
# _resolve_proxy
# ---------------------------------------------------------------------------

class TestResolveProxy:

    def test_direct_vm_returns_host(self, spice_vm):
        """Direct VM (security: null) returns connection host as proxy."""
        result = ProxmoxConnection._resolve_proxy(spice_vm)
        assert result == "100.64.0.9"

    def test_tunnel_vm_returns_localhost(self, tunnel_vm):
        """SSH tunnel VM returns 'localhost' as proxy."""
        result = ProxmoxConnection._resolve_proxy(tunnel_vm)
        assert result == "localhost"

    def test_remote_vm_no_tunnel_returns_host(self):
        """Remote VM without tunnel returns its connection host."""
        vm = {
            "name": "Remote",
            "vmid": 200,
            "server": "testserver",
            "connection": {
                "type": "spice",
                "host": "100.64.0.3",
                "security": None,
            },
        }
        result = ProxmoxConnection._resolve_proxy(vm)
        assert result == "100.64.0.3"


# ---------------------------------------------------------------------------
# _format_vv
# ---------------------------------------------------------------------------

class TestFormatVv:

    def test_produces_virt_viewer_header(self):
        """Output starts with [virt-viewer] header."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert result.startswith("[virt-viewer]\n")

    def test_includes_non_null_fields(self):
        """Non-null fields are included in output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert "host=100.64.0.9" in result
        assert "port=61000" in result
        assert "password=secret" in result

    def test_excludes_null_fields(self):
        """Null fields are excluded from output."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert "tls-port" not in result

    def test_ends_with_newline(self):
        """Output ends with a trailing newline."""
        result = ProxmoxConnection._format_vv(MOCK_SPICE_DATA)
        assert result.endswith("\n")


# ---------------------------------------------------------------------------
# _get_token_secret
# ---------------------------------------------------------------------------

class TestGetTokenSecret:

    def test_returns_secret_from_keyring(self, mock_config):
        """Returns token secret when found in keyring."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value="mysecret"):
            result = conn._get_token_secret("carolyn@pam!pxkit")
        assert result == "mysecret"

    def test_raises_when_secret_not_found(self, mock_config):
        """Raises PxkitConnectionError when keyring returns None."""
        conn = ProxmoxConnection(mock_config)
        with patch("pxkit.connection.keyring.get_password", return_value=None):
            with pytest.raises(PxkitConnectionError, match="not found in keyring"):
                conn._get_token_secret("carolyn@pam!pxkit")

    def test_raises_when_no_keyring_backend(self, mock_config):
        """Raises PxkitConnectionError when no keyring backend is available."""
        conn = ProxmoxConnection(mock_config)
        with patch(
            "pxkit.connection.keyring.get_password",
            side_effect=keyring.errors.NoKeyringError,
        ):
            with pytest.raises(PxkitConnectionError, match="No keyring backend"):
                conn._get_token_secret("carolyn@pam!pxkit")


# ---------------------------------------------------------------------------
# get_spice_ticket
# ---------------------------------------------------------------------------

class TestGetSpiceTicket:

    def test_returns_vv_content(self, mock_config, spice_vm):
        """Returns .vv file content string on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": MOCK_SPICE_DATA}
        mock_response.raise_for_status = MagicMock()

        conn = ProxmoxConnection(mock_config)
        with (
            patch("pxkit.connection.keyring.get_password", return_value="mysecret"),
            patch("pxkit.connection.requests.post", return_value=mock_response),
        ):
            result = conn.get_spice_ticket(spice_vm)

        assert "[virt-viewer]" in result
        assert "host=" in result

    def test_uses_correct_server_for_vm(self, mock_config, spice_vm):
        """get_spice_ticket calls get_server with the VM's server key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": MOCK_SPICE_DATA}
        mock_response.raise_for_status = MagicMock()

        conn = ProxmoxConnection(mock_config)
        with (
            patch("pxkit.connection.keyring.get_password", return_value="mysecret"),
            patch("pxkit.connection.requests.post", return_value=mock_response),
        ):
            conn.get_spice_ticket(spice_vm)

        mock_config.get_server.assert_called_once_with("testserver")

    def test_raises_on_wrong_connection_type(self, mock_config, ssh_vm):
        """Raises PxkitConnectionError when VM type is not spice."""
        conn = ProxmoxConnection(mock_config)
        with pytest.raises(PxkitConnectionError, match="expected 'spice'"):
            conn.get_spice_ticket(ssh_vm)

    def test_raises_on_request_failure(self, mock_config, spice_vm):
        """Raises PxkitConnectionError when API request fails."""
        import requests as req
        conn = ProxmoxConnection(mock_config)
        with (
            patch("pxkit.connection.keyring.get_password", return_value="mysecret"),
            patch(
                "pxkit.connection.requests.post",
                side_effect=req.exceptions.ConnectionError("refused"),
            ),
        ):
            with pytest.raises(PxkitConnectionError, match="Failed to retrieve SPICE ticket"):
                conn.get_spice_ticket(spice_vm)

    def test_raises_when_api_returns_no_data(self, mock_config, spice_vm):
        """Raises PxkitConnectionError when API response has no data field."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": None}
        mock_response.raise_for_status = MagicMock()

        conn = ProxmoxConnection(mock_config)
        with (
            patch("pxkit.connection.keyring.get_password", return_value="mysecret"),
            patch("pxkit.connection.requests.post", return_value=mock_response),
        ):
            with pytest.raises(PxkitConnectionError, match="no data"):
                conn.get_spice_ticket(spice_vm)

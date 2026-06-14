"""
tests/test_config.py - Tests for pxkit.config.

Covers config loading, server lookup, VM list, and error handling.
All tests pass an explicit config_path — no monkeypatching of module
paths, no reliance on default fallback (there is none).
"""

import textwrap
from pathlib import Path

import pytest

from pxkit.config import ConfigManager
from pxkit.exceptions import PxkitConfigError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_CONFIG_YAML = textwrap.dedent("""\
    pxkit:
      servers:
        - name: testserver
          host: 100.64.0.9
          port: 8006
          node: testnode
          token_id: carolyn@pam!pxkit
      terminal:
        app: xfce4-terminal
        exec_flag: -e
      ui:
        title: System Launcher
      vms:
        - name: Puppy Linux
          vmid: 100
          server: testserver
          connection:
            type: spice
            host: 100.64.0.9
            port: ~
            security: ~
""")


@pytest.fixture
def config_file(tmp_path) -> Path:
    """Write a minimal pxkit.yaml and return its path."""
    p = tmp_path / "pxkit.yaml"
    p.write_text(MINIMAL_CONFIG_YAML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ConfigManager — loading
# ---------------------------------------------------------------------------

class TestConfigManagerLoading:

    def test_loads_servers_list(self, config_file):
        """Servers list is loaded correctly."""
        config = ConfigManager(config_path=config_file)
        assert len(config.servers) == 1
        assert config.servers[0]["host"] == "100.64.0.9"

    def test_loads_server_port(self, config_file):
        """Server port is loaded correctly."""
        config = ConfigManager(config_path=config_file)
        assert config.servers[0]["port"] == 8006

    def test_loads_vm_list(self, config_file):
        """VM list is loaded correctly."""
        config = ConfigManager(config_path=config_file)
        assert len(config.vms) == 1
        assert config.vms[0]["name"] == "Puppy Linux"

    def test_loads_terminal_config(self, config_file):
        """Terminal config is loaded correctly."""
        config = ConfigManager(config_path=config_file)
        terminal = config.get("terminal", {})
        assert terminal["app"] == "xfce4-terminal"
        assert terminal["exec_flag"] == "-e"

    def test_loads_ui_title(self, config_file):
        """UI title is loaded correctly."""
        config = ConfigManager(config_path=config_file)
        assert config.get("ui", {}).get("title") == "System Launcher"

    def test_servers_empty_when_absent(self, tmp_path):
        """servers returns empty list when key is absent from config."""
        p = tmp_path / "minimal.yaml"
        p.write_text("pxkit:\n  log_level: normal\n", encoding="utf-8")
        config = ConfigManager(config_path=p)
        assert config.servers == []

    def test_vms_empty_when_absent(self, tmp_path):
        """vms returns empty list when key is absent from config."""
        p = tmp_path / "minimal.yaml"
        p.write_text("pxkit:\n  log_level: normal\n", encoding="utf-8")
        config = ConfigManager(config_path=p)
        assert config.vms == []


# ---------------------------------------------------------------------------
# ConfigManager — get_server
# ---------------------------------------------------------------------------

class TestGetServer:

    def test_returns_matching_server(self, config_file):
        """get_server() returns the correct server dict."""
        config = ConfigManager(config_path=config_file)
        server = config.get_server("testserver")
        assert server["host"] == "100.64.0.9"
        assert server["token_id"] == "carolyn@pam!pxkit"

    def test_raises_for_unknown_name(self, config_file):
        """get_server() raises PxkitConfigError for an unknown server name."""
        config = ConfigManager(config_path=config_file)
        with pytest.raises(PxkitConfigError, match="not found in config"):
            config.get_server("nonexistent")

    def test_error_includes_server_name(self, config_file):
        """Error message includes the requested server name."""
        config = ConfigManager(config_path=config_file)
        with pytest.raises(PxkitConfigError, match="badserver"):
            config.get_server("badserver")


# ---------------------------------------------------------------------------
# ConfigManager — missing config
# ---------------------------------------------------------------------------

class TestConfigManagerMissingConfig:

    def test_raises_when_no_user_config(self, tmp_path):
        """Raises PxkitConfigError with install.sh hint when config missing."""
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(PxkitConfigError, match="Run install.sh"):
            ConfigManager(config_path=missing)

    def test_error_includes_config_path(self, tmp_path):
        """Error message includes the expected config path."""
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(PxkitConfigError, match=str(missing)):
            ConfigManager(config_path=missing)


# ---------------------------------------------------------------------------
# ConfigManager — error handling
# ---------------------------------------------------------------------------

class TestConfigManagerErrors:

    def test_raises_on_malformed_yaml(self, tmp_path):
        """Malformed YAML raises PxkitConfigError."""
        p = tmp_path / "bad.yaml"
        p.write_text("pxkit: {\nbad yaml", encoding="utf-8")
        with pytest.raises(PxkitConfigError, match="Could not read config file"):
            ConfigManager(config_path=p)

    def test_raises_on_unreadable_file(self, tmp_path):
        """Unreadable config file raises PxkitConfigError."""
        p = tmp_path / "unreadable.yaml"
        p.write_text("pxkit:\n  log_level: normal\n", encoding="utf-8")
        p.chmod(0o000)
        with pytest.raises(PxkitConfigError, match="Could not read config file"):
            ConfigManager(config_path=p)
        p.chmod(0o644)  # restore so tmp_path cleanup works

    def test_empty_file_returns_empty_config(self, tmp_path):
        """Empty config file returns empty config without error."""
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        config = ConfigManager(config_path=p)
        assert config.servers == []
        assert config.vms == []


# ---------------------------------------------------------------------------
# ConfigManager.get()
# ---------------------------------------------------------------------------

class TestConfigManagerGet:

    def test_get_returns_value(self, config_file):
        """get() returns the value for an existing key."""
        config = ConfigManager(config_path=config_file)
        assert config.get("terminal") is not None

    def test_get_returns_default_for_missing_key(self, config_file):
        """get() returns the default for a missing key."""
        config = ConfigManager(config_path=config_file)
        assert config.get("nonexistent", "fallback") == "fallback"

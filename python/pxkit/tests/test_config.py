"""
tests/test_config.py - Tests for pxkit.config.

Covers default config loading, user override merging, VM list
replacement, and error handling for missing or malformed files.
No filesystem side effects — all file I/O uses tmp_path.
"""

import textwrap
from pathlib import Path

import pytest
import yaml

from pxkit.config import ConfigManager
from pxkit.exceptions import PxkitConfigError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_DEFAULT_YAML = textwrap.dedent("""\
    pxkit:
      proxmox:
        host: localhost
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
          connection:
            type: spice
            host: localhost
            port: ~
            security: ~
""")

USER_OVERRIDE_YAML = textwrap.dedent("""\
    pxkit:
      proxmox:
        host: 192.168.1.100
      vms:
        - name: Remote VM
          vmid: 200
          connection:
            type: spice
            host: 192.168.1.100
            port: ~
            security: ~
""")


@pytest.fixture
def default_config_file(tmp_path) -> Path:
    """Write a minimal default pxkit.yaml and return its path."""
    p = tmp_path / "pxkit.yaml"
    p.write_text(MINIMAL_DEFAULT_YAML, encoding="utf-8")
    return p


@pytest.fixture
def user_config_file(tmp_path) -> Path:
    """Write a user override pxkit.yaml and return its path."""
    p = tmp_path / "user_pxkit.yaml"
    p.write_text(USER_OVERRIDE_YAML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ConfigManager — default loading
# ---------------------------------------------------------------------------

class TestConfigManagerDefaults:

    def test_loads_proxmox_host(self, default_config_file, monkeypatch):
        """Default proxmox host is loaded correctly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert config.proxmox["host"] == "localhost"

    def test_loads_proxmox_port(self, default_config_file, monkeypatch):
        """Default proxmox port is loaded correctly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert config.proxmox["port"] == 8006

    def test_loads_vm_list(self, default_config_file, monkeypatch):
        """Default VM list is loaded correctly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert len(config.vms) == 1
        assert config.vms[0]["name"] == "Puppy Linux"

    def test_loads_terminal_config(self, default_config_file, monkeypatch):
        """Default terminal config is loaded correctly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        terminal = config.get("terminal", {})
        assert terminal["app"] == "xfce4-terminal"
        assert terminal["exec_flag"] == "-e"

    def test_loads_ui_title(self, default_config_file, monkeypatch):
        """Default UI title is loaded correctly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert config.get("ui", {}).get("title") == "System Launcher"

    def test_vms_empty_when_absent(self, tmp_path, monkeypatch):
        """vms returns empty list when absent from config."""
        p = tmp_path / "minimal.yaml"
        p.write_text("pxkit:\n  proxmox:\n    host: localhost\n", encoding="utf-8")
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", p)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", tmp_path / "nonexistent.yaml")
        config = ConfigManager()
        assert config.vms == []


# ---------------------------------------------------------------------------
# ConfigManager — user overrides
# ---------------------------------------------------------------------------

class TestConfigManagerOverrides:

    def test_user_host_overrides_default(self, default_config_file, user_config_file, monkeypatch):
        """User proxmox host overrides the default."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        config = ConfigManager(config_path=user_config_file)
        assert config.proxmox["host"] == "192.168.1.100"

    def test_non_overridden_keys_preserved(self, default_config_file, user_config_file, monkeypatch):
        """Default keys not present in user config are preserved."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        config = ConfigManager(config_path=user_config_file)
        # port not overridden — should still be 8006
        assert config.proxmox["port"] == 8006

    def test_user_vms_replace_defaults(self, default_config_file, user_config_file, monkeypatch):
        """User VM list replaces default VM list entirely."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        config = ConfigManager(config_path=user_config_file)
        assert len(config.vms) == 1
        assert config.vms[0]["name"] == "Remote VM"
        assert config.vms[0]["vmid"] == 200

    def test_no_user_config_uses_defaults(self, default_config_file, tmp_path, monkeypatch):
        """Missing user config file falls back to defaults cleanly."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        config = ConfigManager(config_path=tmp_path / "nonexistent.yaml")
        assert config.proxmox["host"] == "localhost"


# ---------------------------------------------------------------------------
# ConfigManager — error handling
# ---------------------------------------------------------------------------

class TestConfigManagerErrors:

    def test_raises_on_malformed_yaml(self, tmp_path, monkeypatch):
        """Malformed YAML raises PxkitConfigError."""
        p = tmp_path / "bad.yaml"
        p.write_text("pxkit: {\nbad yaml", encoding="utf-8")
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", p)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", tmp_path / "nonexistent.yaml")
        with pytest.raises(PxkitConfigError, match="Could not read config file"):
            ConfigManager()

    def test_raises_on_unreadable_file(self, tmp_path, monkeypatch):
        """Unreadable config file raises PxkitConfigError."""
        p = tmp_path / "unreadable.yaml"
        p.write_text("pxkit:\n  proxmox:\n    host: localhost\n", encoding="utf-8")
        p.chmod(0o000)
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", p)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", tmp_path / "nonexistent.yaml")
        with pytest.raises(PxkitConfigError, match="Could not read config file"):
            ConfigManager()
        p.chmod(0o644)  # restore so tmp_path cleanup works

    def test_empty_file_returns_empty_config(self, tmp_path, monkeypatch):
        """Empty default config file returns empty config without error."""
        p = tmp_path / "empty.yaml"
        p.write_text("", encoding="utf-8")
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", p)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", tmp_path / "nonexistent.yaml")
        config = ConfigManager()
        assert config.proxmox == {}
        assert config.vms == []


# ---------------------------------------------------------------------------
# ConfigManager.get()
# ---------------------------------------------------------------------------

class TestConfigManagerGet:

    def test_get_returns_value(self, default_config_file, monkeypatch):
        """get() returns the value for an existing key."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert config.get("terminal") is not None

    def test_get_returns_default_for_missing_key(self, default_config_file, monkeypatch):
        """get() returns the default for a missing key."""
        monkeypatch.setattr("pxkit.config._DEFAULT_CONFIG", default_config_file)
        monkeypatch.setattr("pxkit.config._USER_CONFIG", default_config_file.parent / "nonexistent.yaml")
        config = ConfigManager()
        assert config.get("nonexistent", "fallback") == "fallback"

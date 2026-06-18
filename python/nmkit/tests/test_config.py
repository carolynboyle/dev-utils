"""
tests/test_config.py - Tests for nmkit.config.

Covers default loading for both config files, user override merging
for nmkit.yaml, wholesale replacement for connections.yaml, connection
validation, and error handling for missing or malformed files.
No filesystem side effects — all file I/O uses tmp_path.
"""

import textwrap
from pathlib import Path

import pytest

from nmkit.config import ConfigManager, _VALID_OS_HINTS
from nmkit.exceptions import NmkitConfigError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_APP_YAML = textwrap.dedent("""\
    nmkit:
      nxplayer: /usr/NX/bin/nxplayer
      session_dir: ~/Documents/NoMachine
      terminal:
        app: xfce4-terminal
        exec_flag: -e
      ui:
        title: NX Launcher
      log_level: normal
""")

MINIMAL_CONNECTIONS_YAML = textwrap.dedent("""\
    connections:
      - name: Rocky
        host: 192.168.1.100
        port: 22
        user: carolyn
        os: rocky
      - name: Debian
        host: 192.168.1.101
        port: 22
        user: carolyn
        os: debian
""")

USER_APP_OVERRIDE_YAML = textwrap.dedent("""\
    nmkit:
      nxplayer: /usr/local/bin/nxplayer
      ui:
        title: Custom Launcher
""")

USER_CONNECTIONS_YAML = textwrap.dedent("""\
    connections:
      - name: Windows Box
        host: 10.0.0.1
        port: 22
        user: admin
        os: windows
""")


@pytest.fixture
def app_config_file(tmp_path) -> Path:
    """Write a minimal nmkit.yaml and return its path."""
    p = tmp_path / "nmkit.yaml"
    p.write_text(MINIMAL_APP_YAML, encoding="utf-8")
    return p


@pytest.fixture
def connections_file(tmp_path) -> Path:
    """Write a minimal connections.yaml and return its path."""
    p = tmp_path / "connections.yaml"
    p.write_text(MINIMAL_CONNECTIONS_YAML, encoding="utf-8")
    return p


@pytest.fixture
def user_app_config_file(tmp_path) -> Path:
    """Write a user override nmkit.yaml and return its path."""
    p = tmp_path / "user_nmkit.yaml"
    p.write_text(USER_APP_OVERRIDE_YAML, encoding="utf-8")
    return p


@pytest.fixture
def user_connections_file(tmp_path) -> Path:
    """Write a user connections.yaml and return its path."""
    p = tmp_path / "user_connections.yaml"
    p.write_text(USER_CONNECTIONS_YAML, encoding="utf-8")
    return p


def make_config(
    tmp_path,
    monkeypatch,
    app_content=MINIMAL_APP_YAML,
    conn_content=MINIMAL_CONNECTIONS_YAML,
    app_path=None,
    conn_path=None,
):
    """
    Helper: write config files and patch all module-level paths, then
    return a ConfigManager. Patches both default and user config paths
    so tests are fully isolated from real files on disk.
    """
    default_app  = tmp_path / "nmkit.yaml"
    default_conn = tmp_path / "connections.yaml"
    default_app.write_text(app_content, encoding="utf-8")
    default_conn.write_text(conn_content, encoding="utf-8")

    # Nonexistent paths — prevents fallthrough to real user config files.
    absent_user_app  = tmp_path / "absent_user_nmkit.yaml"
    absent_user_conn = tmp_path / "absent_user_connections.yaml"

    monkeypatch.setattr("nmkit.config._DEFAULT_APP_CONFIG",  default_app)
    monkeypatch.setattr("nmkit.config._DEFAULT_CONNECTIONS", default_conn)
    monkeypatch.setattr("nmkit.config._USER_APP_CONFIG",     absent_user_app)
    monkeypatch.setattr("nmkit.config._USER_CONNECTIONS",    absent_user_conn)

    return ConfigManager(
        app_config_path=app_path,
        connections_path=conn_path,
    )


# ---------------------------------------------------------------------------
# ConfigManager — app config loading
# ---------------------------------------------------------------------------

class TestAppConfigLoading:

    def test_loads_nxplayer_path(self, tmp_path, monkeypatch):
        """Default nxplayer path is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["nxplayer"] == "/usr/NX/bin/nxplayer"

    def test_loads_session_dir(self, tmp_path, monkeypatch):
        """Default session_dir is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["session_dir"] == "~/Documents/NoMachine"

    def test_loads_terminal_app(self, tmp_path, monkeypatch):
        """Default terminal app is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["terminal"]["app"] == "xfce4-terminal"

    def test_loads_terminal_exec_flag(self, tmp_path, monkeypatch):
        """Default terminal exec_flag is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["terminal"]["exec_flag"] == "-e"

    def test_loads_ui_title(self, tmp_path, monkeypatch):
        """Default UI title is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["ui"]["title"] == "NX Launcher"

    def test_loads_log_level(self, tmp_path, monkeypatch):
        """Default log level is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.app["log_level"] == "normal"

    def test_get_returns_value(self, tmp_path, monkeypatch):
        """get() returns the value for an existing key."""
        config = make_config(tmp_path, monkeypatch)
        assert config.get("log_level") == "normal"

    def test_get_returns_default_for_missing_key(self, tmp_path, monkeypatch):
        """get() returns the default for a missing key."""
        config = make_config(tmp_path, monkeypatch)
        assert config.get("nonexistent", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# ConfigManager — app config user overrides
# ---------------------------------------------------------------------------

class TestAppConfigOverrides:

    def test_user_nxplayer_overrides_default(
        self, tmp_path, monkeypatch, user_app_config_file
    ):
        """User nxplayer path overrides the default."""
        config = make_config(
            tmp_path, monkeypatch, app_path=user_app_config_file
        )
        assert config.app["nxplayer"] == "/usr/local/bin/nxplayer"

    def test_user_ui_title_overrides_default(
        self, tmp_path, monkeypatch, user_app_config_file
    ):
        """User UI title overrides the default."""
        config = make_config(
            tmp_path, monkeypatch, app_path=user_app_config_file
        )
        assert config.app["ui"]["title"] == "Custom Launcher"

    def test_non_overridden_keys_preserved(
        self, tmp_path, monkeypatch, user_app_config_file
    ):
        """Default keys not in user config are preserved after merge."""
        config = make_config(
            tmp_path, monkeypatch, app_path=user_app_config_file
        )
        assert config.app["terminal"]["app"] == "xfce4-terminal"

    def test_missing_user_app_config_uses_defaults(
        self, tmp_path, monkeypatch
    ):
        """Missing user app config falls back to defaults cleanly."""
        config = make_config(
            tmp_path,
            monkeypatch,
            app_path=tmp_path / "nonexistent.yaml",
        )
        assert config.app["nxplayer"] == "/usr/NX/bin/nxplayer"


# ---------------------------------------------------------------------------
# ConfigManager — connections loading
# ---------------------------------------------------------------------------

class TestConnectionsLoading:

    def test_loads_connection_count(self, tmp_path, monkeypatch):
        """Default connections list has the expected number of entries."""
        config = make_config(tmp_path, monkeypatch)
        assert len(config.connections) == 2

    def test_loads_connection_name(self, tmp_path, monkeypatch):
        """Connection name is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.connections[0]["name"] == "Rocky"

    def test_loads_connection_host(self, tmp_path, monkeypatch):
        """Connection host is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.connections[0]["host"] == "192.168.1.100"

    def test_loads_connection_port(self, tmp_path, monkeypatch):
        """Connection port is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.connections[0]["port"] == 22

    def test_loads_connection_user(self, tmp_path, monkeypatch):
        """Connection user is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.connections[0]["user"] == "carolyn"

    def test_loads_connection_os(self, tmp_path, monkeypatch):
        """Connection os hint is loaded correctly."""
        config = make_config(tmp_path, monkeypatch)
        assert config.connections[0]["os"] == "rocky"

    def test_user_connections_replace_defaults(
        self, tmp_path, monkeypatch, user_connections_file
    ):
        """User connections.yaml replaces defaults entirely."""
        config = make_config(
            tmp_path, monkeypatch, conn_path=user_connections_file
        )
        assert len(config.connections) == 1
        assert config.connections[0]["name"] == "Windows Box"

    def test_unknown_os_hint_normalised(self, tmp_path, monkeypatch):
        """Unknown os hint is normalised to 'unknown'."""
        conn_yaml = textwrap.dedent("""\
            connections:
              - name: Mystery
                host: 10.0.0.1
                port: 22
                user: root
                os: haiku
        """)
        config = make_config(tmp_path, monkeypatch, conn_content=conn_yaml)
        assert config.connections[0]["os"] == "unknown"

    def test_all_valid_os_hints_accepted(self, tmp_path, monkeypatch):
        """All values in _VALID_OS_HINTS are accepted without normalisation."""
        for hint in _VALID_OS_HINTS:
            if hint == "unknown":
                continue  # unknown is the fallback, not a rejection
            conn_yaml = textwrap.dedent(f"""\
                connections:
                  - name: Test
                    host: 10.0.0.1
                    port: 22
                    user: root
                    os: {hint}
            """)
            config = make_config(tmp_path, monkeypatch, conn_content=conn_yaml)
            assert config.connections[0]["os"] == hint


# ---------------------------------------------------------------------------
# ConfigManager — connections validation
# ---------------------------------------------------------------------------

class TestConnectionsValidation:

    def test_entry_missing_host_is_skipped(self, tmp_path, monkeypatch):
        """Connection entry missing 'host' is skipped; valid entries kept."""
        conn_yaml = textwrap.dedent("""\
            connections:
              - name: Bad Entry
                port: 22
                user: root
                os: debian
              - name: Good Entry
                host: 10.0.0.1
                port: 22
                user: root
                os: debian
        """)
        config = make_config(tmp_path, monkeypatch, conn_content=conn_yaml)
        assert len(config.connections) == 1
        assert config.connections[0]["name"] == "Good Entry"

    def test_all_invalid_entries_raises(self, tmp_path, monkeypatch):
        """All invalid entries raises NmkitConfigError."""
        conn_yaml = textwrap.dedent("""\
            connections:
              - name: Bad Entry
                port: 22
                user: root
                os: debian
        """)
        with pytest.raises(NmkitConfigError, match="No valid connections"):
            make_config(tmp_path, monkeypatch, conn_content=conn_yaml)

    def test_empty_connections_list_raises(self, tmp_path, monkeypatch):
        """Empty connections list raises NmkitConfigError."""
        conn_yaml = "connections: []\n"
        with pytest.raises(NmkitConfigError, match="no 'connections' list"):
            make_config(tmp_path, monkeypatch, conn_content=conn_yaml)

    def test_non_dict_entry_is_skipped(self, tmp_path, monkeypatch):
        """Non-dict connection entry is skipped gracefully."""
        conn_yaml = textwrap.dedent("""\
            connections:
              - just a string
              - name: Valid
                host: 10.0.0.1
                port: 22
                user: root
                os: rocky
        """)
        config = make_config(tmp_path, monkeypatch, conn_content=conn_yaml)
        assert len(config.connections) == 1
        assert config.connections[0]["name"] == "Valid"


# ---------------------------------------------------------------------------
# ConfigManager — error handling
# ---------------------------------------------------------------------------

class TestConfigErrors:

    def test_malformed_app_yaml_raises(self, tmp_path, monkeypatch):
        """Malformed nmkit.yaml raises NmkitConfigError."""
        bad_yaml = "nmkit: {\nbad yaml"
        with pytest.raises(NmkitConfigError, match="Could not read config file"):
            make_config(tmp_path, monkeypatch, app_content=bad_yaml)

    def test_malformed_connections_yaml_raises(self, tmp_path, monkeypatch):
        """Malformed connections.yaml raises NmkitConfigError."""
        bad_yaml = "connections: {\nbad yaml"
        with pytest.raises(NmkitConfigError, match="Could not read connections file"):
            make_config(tmp_path, monkeypatch, conn_content=bad_yaml)

    def test_unreadable_app_yaml_raises(self, tmp_path, monkeypatch):
        """Unreadable nmkit.yaml raises NmkitConfigError."""
        default_app  = tmp_path / "nmkit.yaml"
        default_conn = tmp_path / "connections.yaml"
        default_app.write_text(MINIMAL_APP_YAML, encoding="utf-8")
        default_conn.write_text(MINIMAL_CONNECTIONS_YAML, encoding="utf-8")
        default_app.chmod(0o000)

        absent_user_app  = tmp_path / "absent_user_nmkit.yaml"
        absent_user_conn = tmp_path / "absent_user_connections.yaml"

        monkeypatch.setattr("nmkit.config._DEFAULT_APP_CONFIG",  default_app)
        monkeypatch.setattr("nmkit.config._DEFAULT_CONNECTIONS", default_conn)
        monkeypatch.setattr("nmkit.config._USER_APP_CONFIG",     absent_user_app)
        monkeypatch.setattr("nmkit.config._USER_CONNECTIONS",    absent_user_conn)

        try:
            with pytest.raises(NmkitConfigError, match="Could not read config file"):
                ConfigManager()
        finally:
            default_app.chmod(0o644)

    def test_empty_app_yaml_returns_empty_app(self, tmp_path, monkeypatch):
        """Empty nmkit.yaml returns empty app config without error."""
        config = make_config(
            tmp_path, monkeypatch, app_content=""
        )
        assert config.app == {}

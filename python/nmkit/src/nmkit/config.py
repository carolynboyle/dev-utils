"""
nmkit.config - Configuration management for nmkit.

Loads nmkit application config from nmkit.yaml, platform config from
platform.yaml, and connection profiles from connections.yaml. Each file
has its own shipped default in nmkit/data/ and an optional user override
in ~/.config/nmkit/.

nmkit.yaml and platform.yaml are merged recursively — only keys present
in the user file override their defaults. connections.yaml is replaced
wholesale if a user override exists.

The user ~/.config/nmkit/platform.yaml is written by the installer with
flat values for the detected OS. It contains no nested OS keys — just
ready-to-use values for the platform the package was installed on. If
nmkit is moved to a different platform, the installer must be re-run.

Usage:
    from nmkit.config import ConfigManager

    config = ConfigManager()
    open_cmd = config.platform['open_command']
    for host in config.connections:
        print(host['name'])

User overrides:
    ~/.config/nmkit/nmkit.yaml       — app settings (merged)
    ~/.config/nmkit/platform.yaml    — platform settings (merged)
    ~/.config/nmkit/connections.yaml — connection list (replaced wholesale)
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from nmkit.exceptions import NmkitConfigError

log = logging.getLogger("nmkit")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR                = Path(__file__).parent / "data"
_DEFAULT_APP_CONFIG      = _DATA_DIR / "nmkit.yaml"
_DEFAULT_PLATFORM_CONFIG = _DATA_DIR / "platform.yaml"
_DEFAULT_CONNECTIONS     = _DATA_DIR / "connections.yaml"
_USER_CONFIG_DIR         = Path.home() / ".config" / "nmkit"
_USER_APP_CONFIG         = _USER_CONFIG_DIR / "nmkit.yaml"
_USER_PLATFORM_CONFIG    = _USER_CONFIG_DIR / "platform.yaml"
_USER_CONNECTIONS        = _USER_CONFIG_DIR / "connections.yaml"

# Valid OS hint values — anything else renders as 'unknown'.
_VALID_OS_HINTS = frozenset({
    "debian", "ubuntu", "rocky", "rhel", "fedora",
    "opensuse", "arch", "windows", "macos", "unknown",
})


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Loads and exposes nmkit configuration from three YAML files.

    nmkit.yaml provides application settings (session_dir, UI title,
    log level). platform.yaml provides platform-specific paths and
    commands as flat values written by the installer for the current OS.
    connections.yaml provides the list of hosts to display in the main
    window.

    The three files are loaded and validated independently so a malformed
    file cannot corrupt the others.

    Usage:
        config = ConfigManager()
        open_cmd = config.platform['open_command']
        for conn in config.connections:
            print(conn['name'], conn['host'])
    """

    def __init__(
        self,
        app_config_path: Optional[Path] = None,
        platform_config_path: Optional[Path] = None,
        connections_path: Optional[Path] = None,
    ):
        """
        Initialise ConfigManager.

        Args:
            app_config_path:      Override path to the user nmkit.yaml.
                                  Defaults to ~/.config/nmkit/nmkit.yaml.
            platform_config_path: Override path to the user platform.yaml.
                                  Defaults to ~/.config/nmkit/platform.yaml.
            connections_path:     Override path to the user connections.yaml.
                                  Defaults to ~/.config/nmkit/connections.yaml.
                                  Useful for testing.
        """
        self._app         = self._load_app(app_config_path)
        self._platform    = self._load_platform(platform_config_path)
        self._connections = self._load_connections(connections_path)

    # -- Public interface -----------------------------------------------------

    @property
    def app(self) -> dict:
        """
        Application settings from nmkit.yaml.

        Returns:
            Dict with keys: session_dir, ui, log_level.
        """
        return self._app

    @property
    def platform(self) -> dict:
        """
        Platform settings from platform.yaml.

        Written by the installer with flat values for the current OS.
        Keys: open_command, nxplayer, terminal.

        Returns:
            Dict of platform values for the installed OS.
        """
        return self._platform

    @property
    def connections(self) -> list:
        """
        Connection profiles from connections.yaml.

        Returns:
            List of connection dicts, each with keys:
            name, host, port, user, os.
        """
        return self._connections

    def get(self, key: str, default=None):
        """
        Return a top-level value from the app config by key.

        Args:
            key:     Top-level key within the nmkit app config section.
            default: Value to return if the key is absent.

        Returns:
            The config value, or default if not found.
        """
        return self._app.get(key, default)

    def save_connections(self, connections: list) -> None:
        """
        Write a connection list to the user connections.yaml file.

        Creates the config directory if it does not exist. Updates
        the in-memory connections list so callers see the change
        immediately without reloading.

        Args:
            connections: List of connection dicts, each with keys:
                         name, host, port, user, os.

        Raises:
            NmkitConfigError: If the file cannot be written.
        """
        _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        try:
            _USER_CONNECTIONS.write_text(
                yaml.dump({"connections": connections}, default_flow_style=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise NmkitConfigError(
                f"Could not write connections file {_USER_CONNECTIONS}: {exc}"
            ) from exc

        self._connections = connections
        log.info("Saved %d connection(s) to %s", len(connections), _USER_CONNECTIONS)

    # -- Internal: app config -------------------------------------------------

    @staticmethod
    def _load_app(config_path: Optional[Path]) -> dict:
        """
        Load and merge default and user nmkit.yaml files.

        Args:
            config_path: Explicit user config path override, or None
                         to use ~/.config/nmkit/nmkit.yaml.

        Returns:
            Merged app config dict.

        Raises:
            NmkitConfigError: If a config file exists but cannot be
                              read or parsed.
        """
        defaults  = ConfigManager._load_section(_DEFAULT_APP_CONFIG, "nmkit")
        user_path = config_path or _USER_APP_CONFIG

        if user_path.exists():
            user = ConfigManager._load_section(user_path, "nmkit")
            log.debug("Loaded user app config from %s", user_path)
            return ConfigManager._merge(defaults, user)

        log.debug("No user app config found; using defaults")
        return defaults

    # -- Internal: platform config --------------------------------------------

    @staticmethod
    def _load_platform(config_path: Optional[Path]) -> dict:
        """
        Load and merge default and user platform.yaml files.

        The user platform.yaml is written by the installer with flat
        values for the detected OS — no nested OS keys. The shipped
        default at src/nmkit/data/platform.yaml retains the nested
        structure as a reference but is not used at runtime unless no
        user file exists (e.g. during development without installing).

        Args:
            config_path: Explicit user config path override, or None
                         to use ~/.config/nmkit/platform.yaml.

        Returns:
            Merged platform config dict with flat values.

        Raises:
            NmkitConfigError: If a config file exists but cannot be
                              read or parsed.
        """
        user_path = config_path or _USER_PLATFORM_CONFIG

        if user_path.exists():
            user = ConfigManager._load_section(user_path, "platform")
            log.debug("Loaded user platform config from %s", user_path)
            # User file is flat — no default merge needed.
            # Individual keys may still be overridden by merging with
            # an existing user file on top of itself (idempotent).
            return user

        # Fallback to shipped default during development or if installer
        # was not run. The nested structure means we cannot resolve
        # platform keys without OS detection, so return the raw dict
        # and let callers handle missing keys gracefully.
        log.warning(
            "No user platform config found at %s. "
            "Run the installer to generate a platform-specific config.",
            _USER_PLATFORM_CONFIG,
        )
        return ConfigManager._load_section(_DEFAULT_PLATFORM_CONFIG, "platform")

    # -- Internal: connections ------------------------------------------------

    @staticmethod
    def _load_connections(connections_path: Optional[Path]) -> list:
        """
        Load the connections list from connections.yaml.

        User connections.yaml replaces the shipped defaults entirely —
        it is not merged. Validates each entry for required fields and
        logs a warning for unknown os hint values.

        Args:
            connections_path: Explicit path override, or None to use
                              ~/.config/nmkit/connections.yaml.

        Returns:
            List of validated connection dicts.

        Raises:
            NmkitConfigError: If the file exists but cannot be read,
                              parsed, or contains no valid connections.
        """
        path = connections_path or _USER_CONNECTIONS

        if not path.exists():
            path = _DEFAULT_CONNECTIONS
            log.debug("No user connections file found; using defaults")

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise NmkitConfigError(
                f"Could not read connections file {path}: {exc}"
            ) from exc

        if not data or not isinstance(data, dict):
            raise NmkitConfigError(
                f"Connections file {path} is empty or not a YAML mapping."
            )

        raw = data.get("connections", [])
        if not isinstance(raw, list) or not raw:
            raise NmkitConfigError(
                f"Connections file {path} has no 'connections' list."
            )

        return ConfigManager._validate_connections(raw)

    @staticmethod
    def _validate_connections(raw: list) -> list:
        """
        Validate each connection entry and return the cleaned list.

        Required fields: name, host, port, user, os.
        Entries missing required fields are skipped with a warning.
        Unknown os hint values are accepted but logged.

        Args:
            raw: List of raw connection dicts from YAML.

        Returns:
            List of validated connection dicts.

        Raises:
            NmkitConfigError: If no valid connections remain after
                              filtering invalid entries.
        """
        required = {"name", "host", "port", "user", "os"}
        valid    = []

        for entry in raw:
            if not isinstance(entry, dict):
                log.warning("Skipping non-dict connection entry: %r", entry)
                continue

            missing = required - entry.keys()
            if missing:
                log.warning(
                    "Skipping connection %r — missing fields: %s",
                    entry.get("name", "<unnamed>"),
                    ", ".join(sorted(missing)),
                )
                continue

            os_hint = str(entry["os"]).lower()
            if os_hint not in _VALID_OS_HINTS:
                log.warning(
                    "Connection %r has unknown os hint %r — "
                    "will render as 'unknown'.",
                    entry["name"],
                    os_hint,
                )
                entry = dict(entry)
                entry["os"] = "unknown"

            valid.append(entry)

        if not valid:
            raise NmkitConfigError(
                "No valid connections found in connections.yaml."
            )

        log.debug("Loaded %d connection(s)", len(valid))
        return valid

    # -- Internal: helpers ----------------------------------------------------

    @staticmethod
    def _load_section(path: Path, section: str) -> dict:
        """
        Load a named top-level section from a YAML file.

        Args:
            path:    Path to the YAML file.
            section: Top-level section key to extract.

        Returns:
            Dict of key/value pairs from the section, or empty dict
            if the section is absent.

        Raises:
            NmkitConfigError: If the file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise NmkitConfigError(
                f"Could not read config file {path}: {exc}"
            ) from exc

        if not data or not isinstance(data, dict):
            return {}

        return data.get(section, {})

    @staticmethod
    def _merge(base: dict, override: dict) -> dict:
        """
        Recursively merge override into base.

        Keys present in override replace or extend those in base.
        Keys absent from override are left unchanged.
        List values are replaced wholesale, not appended.

        Args:
            base:     Default config dict.
            override: User config dict.

        Returns:
            Merged dict.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._merge(result[key], value)
            else:
                result[key] = value
        return result

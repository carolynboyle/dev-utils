# config.py

**Path:** python/setupkit/src/setupkit/config.py
**Syntax:** python
**Generated:** 2026-05-11 15:11:09

```python
"""
setupkit.config - Configuration management for setupkit.

Loads setupkit defaults from the shipped setupkit.yaml in setupkit/data/,
with optional user overrides from the 'setupkit:' section of
~/.config/dev-utils/config.yaml. User values are merged over defaults —
only keys present in the user file are overridden.

This is the single source of truth for all paths used by setupkit.
Other modules import ConfigManager rather than hardcoding paths.

Usage:
    from setupkit.config import ConfigManager

    config = ConfigManager()
    config_dir = config.config_dir
    log_path   = config.log_path

User overrides (~/.config/dev-utils/config.yaml):
    setupkit:
      config_dir: ~/.config/dev-utils/setupkit
      log_dir: ~/.local/share/dev-utils
"""

from pathlib import Path
from typing import Optional

import yaml

from setupkit.exceptions import PluginConfigError


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR       = Path(__file__).parent / "data"
_DEFAULT_CONFIG = _DATA_DIR / "setupkit.yaml"
_USER_CONFIG    = Path.home() / ".config" / "dev-utils" / "config.yaml"


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Loads and merges setupkit configuration.

    Shipped defaults in setupkit/data/setupkit.yaml are the baseline.
    User overrides in the 'setupkit:' section of
    ~/.config/dev-utils/config.yaml are merged on top.

    Exposes resolved Path objects for all directories and files used
    by setupkit. Tilde (~) in config values is expanded automatically.

    Usage:
        config = ConfigManager()
        config_dir = config.config_dir
        log_path   = config.log_path
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise ConfigManager.

        Args:
            config_path: Override path to the user config file. Defaults
                         to ~/.config/dev-utils/config.yaml. Useful for
                         testing.
        """
        self._config = self._load(config_path)

    # -- Public interface -----------------------------------------------------

    def get(self, key: str, default=None):
        """
        Return a value from the setupkit config section by key.

        Args:
            key:     Key within the setupkit section.
            default: Value to return if the key is absent.

        Returns:
            The config value, or default if not found.
        """
        return self._config.get(key, default)

    @property
    def config_dir(self) -> Path:
        """
        Path to the directory containing plugin config yaml files.

        Returns:
            Resolved Path to ~/.config/dev-utils/setupkit or user override.
        """
        return Path(self._config["config_dir"]).expanduser().resolve()

    @property
    def log_dir(self) -> Path:
        """
        Path to the directory where setupkit writes log files.

        Returns:
            Resolved Path to ~/.local/share/dev-utils or user override.
        """
        return Path(self._config["log_dir"]).expanduser().resolve()

    @property
    def log_path(self) -> Path:
        """
        Path to the setupkit plain text log file.

        Returns:
            Resolved Path to <log_dir>/setupkit.log.
        """
        return self.log_dir / "setupkit.log"

    @property
    def venv_path(self) -> Path:
        """
        Path to the shared tools virtual environment.

        This is the venv into which all Project Crew tools are installed.
        Defaults to /opt/venvs/tools. Override in
        ~/.config/dev-utils/config.yaml under the setupkit: section.

        Returns:
            Resolved Path to the tools venv directory.
        """
        return Path(self._config.get("venv_path", "/opt/venvs/tools")).expanduser().resolve()

    # -- Internal -------------------------------------------------------------

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """
        Load and merge default and user config files.

        Reads the shipped setupkit.yaml defaults, then merges the
        'setupkit:' section from the user's dev-utils config.yaml
        on top if it exists.

        Args:
            config_path: Explicit user config path override, or None
                         to use ~/.config/dev-utils/config.yaml.

        Returns:
            Merged setupkit config dict.

        Raises:
            PluginConfigError: If a config file exists but cannot be
                               read or parsed.
        """
        defaults = ConfigManager._load_section(_DEFAULT_CONFIG, "setupkit")
        user_path = config_path or _USER_CONFIG

        if user_path.exists():
            user = ConfigManager._load_section(user_path, "setupkit")
            return ConfigManager._merge(defaults, user)

        return defaults

    @staticmethod
    def _load_section(path: Path, section: str) -> dict:
        """
        Load a named section from a YAML file.

        Args:
            path:    Path to the YAML file.
            section: Top-level section key to extract.

        Returns:
            Dict of key/value pairs from the section, or empty dict
            if the section is absent.

        Raises:
            PluginConfigError: If the file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise PluginConfigError(
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

```

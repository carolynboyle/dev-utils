"""
pxkit.config - Configuration management for pxkit.

Loads pxkit defaults from the shipped pxkit.yaml in pxkit/data/,
with optional user overrides from ~/.config/pxkit/pxkit.yaml.
User values are merged over defaults — only keys present in the user
file are overridden. The exception is the 'vms' list, which is replaced
wholesale if present in the user config.

Usage:
    from pxkit.config import ConfigManager

    config = ConfigManager()
    proxmox = config.proxmox
    vms     = config.vms

User overrides (~/.config/pxkit/pxkit.yaml):
    pxkit:
      proxmox:
        host: 192.168.1.100
      vms:
        - name: My VM
          vmid: 100
          connection:
            host: 192.168.1.100
            port: ~
            security: ~
"""

from pathlib import Path
from typing import Optional

import yaml

from pxkit.exceptions import PxkitConfigError


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR       = Path(__file__).parent / "data"
_DEFAULT_CONFIG = _DATA_DIR / "pxkit.yaml"
_USER_CONFIG    = Path.home() / ".config" / "pxkit" / "pxkit.yaml"


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Loads and merges pxkit configuration.

    Shipped defaults in pxkit/data/pxkit.yaml are the baseline.
    User overrides in ~/.config/pxkit/pxkit.yaml are merged on top.

    The 'proxmox' section is merged recursively — only keys present in
    the user file override their defaults. The 'vms' list is replaced
    entirely if present in the user config.

    Usage:
        config = ConfigManager()
        proxmox_host = config.proxmox['host']
        for vm in config.vms:
            print(vm['name'])
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise ConfigManager.

        Args:
            config_path: Override path to the user config file. Defaults
                         to ~/.config/pxkit/pxkit.yaml. Useful for testing.
        """
        self._config = self._load(config_path)

    # -- Public interface -----------------------------------------------------

    @property
    def proxmox(self) -> dict:
        """
        Proxmox connection settings.

        Returns:
            Dict with keys: host, port, node, token_id.
            Token secret is never stored here — retrieve via keyring.
        """
        return self._config.get("proxmox", {})

    @property
    def vms(self) -> list:
        """
        List of configured VMs.

        Returns:
            List of VM dicts, each with keys: name, vmid, connection.
            connection contains: host, port, security.
        """
        return self._config.get("vms", [])

    def get(self, key: str, default=None):
        """
        Return a value from the pxkit config section by key.

        Args:
            key:     Top-level key within the pxkit section.
            default: Value to return if the key is absent.

        Returns:
            The config value, or default if not found.
        """
        return self._config.get(key, default)

    # -- Internal -------------------------------------------------------------

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """
        Load and merge default and user config files.

        Reads the shipped pxkit.yaml defaults, then merges the user's
        ~/.config/pxkit/pxkit.yaml on top if it exists.

        The 'vms' list is treated as a unit — if present in user config
        it replaces the default list entirely.

        Args:
            config_path: Explicit user config path override, or None
                         to use ~/.config/pxkit/pxkit.yaml.

        Returns:
            Merged pxkit config dict.

        Raises:
            PxkitConfigError: If a config file exists but cannot be
                              read or parsed.
        """
        defaults = ConfigManager._load_section(_DEFAULT_CONFIG, "pxkit")
        user_path = config_path or _USER_CONFIG

        if user_path.exists():
            user = ConfigManager._load_section(user_path, "pxkit")
            return ConfigManager._merge(defaults, user)

        return defaults

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
            PxkitConfigError: If the file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise PxkitConfigError(
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
        List values (e.g. 'vms') are replaced wholesale, not appended.

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
                # Covers both scalar overrides and list replacement (vms)
                result[key] = value
        return result
